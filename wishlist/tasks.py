from celery import shared_task, current_task
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from .models import Item, Product, PriceHistory, ImportRun
from .parsers import get_parser
import logging
from django.utils import timezone
from decimal import Decimal
import hashlib
from datetime import timedelta

logger = logging.getLogger(__name__)
PARSED_PRODUCT_CACHE_TTL = int(getattr(settings, 'PARSED_PRODUCT_CACHE_TTL', 172800))
PARSED_PRODUCT_FRESH_FOR = timedelta(seconds=PARSED_PRODUCT_CACHE_TTL)


def _parsed_product_cache_key(marketplace, article_code=None, url=None):
    if article_code:
        key_suffix = str(article_code)
    elif url:
        key_suffix = hashlib.sha1(url.encode('utf-8')).hexdigest()
    else:
        key_suffix = 'unknown'
    return f"parsed_product:{marketplace}:{key_suffix}"


def _product_needs_enrichment(product):
    """Определяет, нужно ли заново парсить товар из внешнего источника."""
    if not product:
        return True

    if not product.name or product.price is None or not product.image_url:
        return True

    if not product.last_price_check:
        return True

    if timezone.now() - product.last_price_check >= PARSED_PRODUCT_FRESH_FOR:
        return True

    return False


def _to_decimal_or_none(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_int_or_none(value):
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _extract_wb_urls_from_raw_data(raw_data):
    """Нормализует входные данные и возвращает список URL WB товаров"""
    import json
    import re

    if not raw_data:
        return []

    text = raw_data.strip()
    tokens = []

    # 1) JSON массив
    if text.startswith('[') and text.endswith(']'):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                tokens.extend([str(v).strip() for v in parsed if str(v).strip()])
        except Exception:
            pass

    # 2) Текст со ссылками/артикулами
    if not tokens:
        normalized = text.replace(';', '\n').replace(',', '\n')
        tokens.extend([line.strip() for line in normalized.splitlines() if line.strip()])

    url_pattern = re.compile(r'https?://[^\s]+', re.IGNORECASE)
    wb_urls = []
    seen = set()

    for token in tokens:
        url_match = url_pattern.search(token)
        if url_match:
            url = url_match.group(0).strip()
            if 'wildberries.ru' in url.lower() or 'wb.ru' in url.lower():
                # Убираем лишние query-параметры (кроме базового пути товара)
                clean = url.split('?')[0]
                if clean not in seen:
                    seen.add(clean)
                    wb_urls.append(clean)
            continue

    return wb_urls


def _extract_wb_entries_from_raw_data(raw_data):
    """
    Извлекает пары {name, url, article_code} из WB share-текста.

    Пример блока:
        Название товара
        https://www.wildberries.ru/catalog/123/detail.aspx?size=...
    """
    import re

    if not raw_data:
        return []

    url_pattern = re.compile(r'https?://[^\s]+', re.IGNORECASE)
    article_pattern = re.compile(r'/catalog/(\d+)/', re.IGNORECASE)

    lines = [line.strip() for line in raw_data.splitlines()]
    entries = []
    seen_articles = set()

    last_title = None
    for line in lines:
        if not line:
            continue

        url_match = url_pattern.search(line)
        if not url_match:
            last_title = line
            continue

        raw_url = url_match.group(0).strip()
        if 'wildberries.ru' not in raw_url.lower() and 'wb.ru' not in raw_url.lower():
            continue

        clean_url = raw_url.split('?')[0]
        article_match = article_pattern.search(clean_url)
        article_code = article_match.group(1) if article_match else None

        if not article_code:
            continue

        if article_code in seen_articles:
            last_title = None
            continue

        seen_articles.add(article_code)
        entries.append({
            'article_code': article_code,
            'url': f"https://www.wildberries.ru/catalog/{article_code}/detail.aspx",
            'name': last_title if last_title else f"Товар {article_code}",
        })
        last_title = None

    return entries


def _build_wb_default_image_url(article_code):
    """Формирует fallback URL более качественной картинки WB"""
    if not article_code:
        return None

    try:
        volume = article_code[:4]
        part = article_code[:6]
        return f"https://basket-01.wbbasket.ru/vol{volume}/part{part}/{article_code}/images/big/1.webp"
    except Exception:
        return None


def detect_marketplace(url):
    """
    Автоматическое определение маркетплейса по URL

    Args:
        url: URL товара

    Returns:
        str: 'wildberries', 'ozon', или 'other'
    """
    url_lower = url.lower()

    if 'wildberries.ru' in url_lower or 'wb.ru' in url_lower:
        return 'wildberries'
    elif 'ozon.ru' in url_lower:
        return 'ozon'
    elif 'market.yandex.ru' in url_lower or 'pokupki.market.yandex.ru' in url_lower:
        return 'yandex_market'
    else:
        return 'other'


def extract_article_code(url, marketplace):
    """
    Извлечь артикул товара из URL

    Args:
        url: URL товара
        marketplace: Маркетплейс ('wildberries', 'ozon', etc.)

    Returns:
        str or None: Артикул товара или None
    """
    import re

    if marketplace == 'wildberries':
        article_match = re.search(r'/catalog/(\d+)/', url)
        return article_match.group(1) if article_match else None
    elif marketplace == 'ozon':
        article_match = re.search(r'/product/[^/]+-(\d+)', url)
        return article_match.group(1) if article_match else None
    return None


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
)
def update_prices():
    """
    Обновить цены всех активных товаров.

    Использует одну Selenium-сессию на весь batch для экономии ресурсов.
    WB API закрыт x-pow challenge, поэтому парсим через Selenium напрямую.
    """
    from .selenium_parser import SeleniumWildberriesParser

    products = (
        Product.objects.filter(
            item__is_active=True,
            item__isnull=False,
            marketplace='wildberries',
        )
        .distinct()
    )

    total = products.count()
    if total == 0:
        return "No active products to update"

    updated_count = 0
    error_count = 0

    with SeleniumWildberriesParser(headless=True) as parser:
        for product in products:
            try:
                if not product.url:
                    continue

                cache_key = _parsed_product_cache_key(
                    'wildberries', article_code=product.article_code, url=product.url
                )
                result = cache.get(cache_key)
                if not result:
                    result = parser.parse(product.url, timeout=25)
                    if result:
                        cache.set(cache_key, result, timeout=PARSED_PRODUCT_CACHE_TTL)

                if result and result.get('price'):
                    new_price = _to_decimal_or_none(result['price'])
                    if new_price is None:
                        error_count += 1
                        continue

                    changed_fields = ['last_price_check']
                    product.last_price_check = timezone.now()

                    if new_price != product.price:
                        PriceHistory.objects.create(product=product, price=new_price)
                        product.price = new_price
                        changed_fields.append('price')
                        logger.info(f"Price updated: {product.name}: {product.price} -> {new_price}")

                    if result.get('name'):
                        product.name = result['name']
                        changed_fields.append('name')
                    if result.get('image_url') and not product.image_url:
                        product.image_url = result['image_url']
                        changed_fields.append('image_url')

                    product.save(update_fields=changed_fields)
                    updated_count += 1
                else:
                    logger.warning(f"Could not fetch price for {product.name}")
                    error_count += 1

            except Exception as e:
                logger.error(f"Error updating {product.name}: {e}", exc_info=True)
                error_count += 1

    result_msg = f"Price update: {updated_count} updated, {error_count} errors, {total} total"
    logger.info(result_msg)
    return result_msg


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 30},
)
def update_item_price(item_id):
    """
    Обновить цену конкретного товара

    Args:
        item_id: ID товара в базе данных

    Returns:
        Строка с результатом обновления
    """
    try:
        item = Item.objects.select_related('product').get(id=item_id, is_active=True)
        product = item.product

        if not product:
            return f"Item {item_id} has no associated product"

        parser = get_parser(product.marketplace)
        if not parser:
            return f"No parser available for {product.marketplace}"

        result = parser.parse(product.url)

        if result and result.get('price'):
            new_price = result['price']

            if new_price != product.price:
                PriceHistory.objects.create(product=product, price=new_price)
                old_price = product.price
                product.price = new_price

                if result.get('name'):
                    product.name = result['name']

                product.last_price_check = timezone.now()
                product.save()

                logger.info(f"Updated {product.name}: {old_price} -> {new_price} ₽")
                return f"Price updated: {old_price} -> {new_price} ₽"
            else:
                return f"Price unchanged: {product.price} ₽"
        else:
            logger.warning(f"Could not fetch price for item {item_id}")
            return "Failed to fetch price"

    except Item.DoesNotExist:
        logger.error(f"Item {item_id} not found")
        return f"Item {item_id} not found"
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {e}", exc_info=True)
        raise  # Перебросить для retry


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 30},
)
def add_item_from_url(user_id, url):
    """
    Асинхронное добавление товара по URL

    Args:
        user_id: ID пользователя
        url: URL товара с маркетплейса

    Returns:
        dict: {'success': bool, 'item_id': int, 'message': str}
    """
    from django.contrib.auth.models import User
    import re

    try:
        # Очищаем URL - извлекаем только ссылку из текста
        # Иногда пользователи копируют "Название товара https://..."
        url = url.strip()
        url_match = re.search(r'https?://[^\s]+', url)
        if url_match:
            url = url_match.group(0)

        # Получаем пользователя
        user = User.objects.get(id=user_id)

        # Определяем маркетплейс
        marketplace = detect_marketplace(url)
        logger.info(f"Detected marketplace: {marketplace} for URL: {url}")

        # Извлекаем артикул из URL
        article_code = extract_article_code(url, marketplace)

        # Пытаемся найти товар в глобальном каталоге
        product = None
        result = None
        if article_code:
            product = Product.objects.filter(article_code=article_code).first()
            if product:
                logger.info(f"Found product in catalog: {product.name}")

        # Если товар не найден в каталоге - парсим
        if not product:
            logger.info(f"Product not in catalog, parsing from {url}...")
            cache_key = _parsed_product_cache_key(marketplace, article_code=article_code, url=url)
            result = cache.get(cache_key)

            if result:
                logger.info(f"Using cached parsed result for {marketplace}:{article_code or url}")
            else:
                # Для Wildberries/Ozon используем Selenium парсер
                if marketplace == 'wildberries':
                    from .selenium_parser import parse_with_selenium
                    result = parse_with_selenium(url, headless=True)
                elif marketplace == 'ozon':
                    from .selenium_parser import parse_ozon_product_with_selenium
                    result = parse_ozon_product_with_selenium(url, headless=True)
                else:
                    # Для других маркетплейсов используем старый парсер
                    parser = get_parser(marketplace)
                    if not parser:
                        return {
                            'success': False,
                            'message': f'Парсер для {marketplace} не доступен'
                        }
                    result = parser.parse(url)

                if result:
                    cache.set(cache_key, result, timeout=PARSED_PRODUCT_CACHE_TTL)

            if not result:
                return {
                    'success': False,
                    'message': 'Не удалось получить данные о товаре'
                }

            # Проверяем, что получили минимально необходимые данные
            if not result.get('name') and not result.get('price'):
                return {
                    'success': False,
                    'message': 'Не удалось получить данные о товаре'
                }

            # Создаём товар в глобальном каталоге
            product_name = result.get('name') or f"Товар {article_code or 'без артикула'}"

            product = Product.objects.create(
                article_code=article_code or f"manual_{user.id}_{timezone.now().timestamp()}",
                name=product_name,
                marketplace=marketplace,
                url=url,
                price=result.get('price'),
                image_url=result.get('image_url'),
                brand=result.get('brand'),
                category=result.get('category'),
                rating=_to_decimal_or_none(result.get('rating')),
                reviews_count=_to_int_or_none(result.get('reviews_count')),
                last_price_check=timezone.now()
            )
            logger.info(f"Created new product in catalog: {product.name}")

        # Обогащаем существующий товар из уже полученного результата парсинга
        # (без повторного Selenium-запроса)
        if product and article_code and result:
            changed_fields = []
            if result.get('category') and not product.category:
                product.category = result['category']
                changed_fields.append('category')
            enriched_rating = _to_decimal_or_none(result.get('rating'))
            if enriched_rating is not None and product.rating is None:
                product.rating = enriched_rating
                changed_fields.append('rating')
            enriched_reviews = _to_int_or_none(result.get('reviews_count'))
            if enriched_reviews is not None and product.reviews_count is None:
                product.reviews_count = enriched_reviews
                changed_fields.append('reviews_count')
            if result.get('image_url') and not product.image_url:
                product.image_url = result['image_url']
                changed_fields.append('image_url')
            if result.get('brand') and not product.brand:
                product.brand = result['brand']
                changed_fields.append('brand')
            if changed_fields:
                product.last_price_check = timezone.now()
                changed_fields.append('last_price_check')
                product.save(update_fields=changed_fields)

        # Проверяем, не добавлен ли уже этот товар в wishlist пользователя
        existing_item = Item.objects.select_related('product').filter(user=user, product=product).first()
        if existing_item:
            if not existing_item.is_active:
                existing_item.is_active = True
                existing_item.save(update_fields=['is_active'])
                logger.info(f"Reactivated item {existing_item.id} in user wishlist: {product.name}")
                return {
                    'success': True,
                    'item_id': existing_item.id,
                    'message': 'Товар восстановлен в wishlist',
                    'item': {
                        'id': existing_item.id,
                        'name': product.name,
                        'price': str(product.price) if product.price else None,
                        'marketplace': product.marketplace,
                        'elo_rating': existing_item.elo_rating
                    }
                }

            return {
                'success': False,
                'message': 'Этот товар уже в вашем списке',
                'item_id': existing_item.id
            }

        # Добавляем товар в wishlist пользователя
        item = Item.objects.create(
            user=user,
            product=product
        )

        logger.info(f"Successfully added item {item.id} to user wishlist: {product.name}")

        return {
            'success': True,
            'item_id': item.id,
            'message': 'Товар успешно добавлен в wishlist',
            'item': {
                'id': item.id,
                'name': product.name,
                'price': str(product.price) if product.price else None,
                'marketplace': product.marketplace,
                'elo_rating': item.elo_rating
            }
        }

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {
            'success': False,
            'message': 'Пользователь не найден'
        }
    except Exception as e:
        logger.error(f"Error adding item from URL: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Ошибка при добавлении товара: {str(e)}'
        }


def add_item_by_url_task(user_id, url):
    """Совместимость со старым кодом импорта избранного"""
    return add_item_from_url(user_id, url)


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 60})
def add_items_from_catalog(user_id, catalog_url, max_items=100):
    """
    Парсит каталог и сохраняет товары в глобальный каталог Product
    (НЕ добавляет в wishlist пользователя)

    Args:
        user_id: ID пользователя (не используется, сохранено для совместимости)
        catalog_url: URL страницы каталога
        max_items: Максимальное количество товаров для парсинга

    Returns:
        Dict с результатами
    """
    try:
        logger.info(f"Parsing catalog {catalog_url}, max {max_items} items")

        # Определяем маркетплейс
        marketplace = detect_marketplace(catalog_url)
        if marketplace != 'wildberries':
            return {
                'success': False,
                'message': 'Поддерживаются только каталоги Wildberries'
            }

        # Парсим каталог через Selenium (обновлённый парсер с правильными селекторами)
        from .selenium_parser import parse_catalog_with_selenium

        logger.info("Starting catalog parsing with Selenium...")
        products = parse_catalog_with_selenium(catalog_url, max_items=max_items, headless=True)

        if not products:
            return {
                'success': False,
                'message': 'Не удалось получить товары из каталога'
            }

        logger.info(f"Got {len(products)} products from catalog")

        # Сохраняем товары в глобальный каталог Product
        added_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        for product_data in products:
            try:
                article_code = product_data.get('article_code')
                if not article_code:
                    continue

                product_name = product_data.get('name') or f"Товар {article_code}"

                # Ищем существующий товар или создаём новый
                product, created = Product.objects.update_or_create(
                    article_code=article_code,
                    defaults={
                        'name': product_name,
                        'marketplace': marketplace,
                        'url': product_data.get('url'),
                        'price': product_data.get('price'),
                        'image_url': product_data.get('image_url'),
                        'last_price_check': timezone.now()
                    }
                )

                if created:
                    added_count += 1
                    logger.info(f"Added new product {added_count}: {product.name[:50]}")
                else:
                    updated_count += 1
                    logger.debug(f"Updated product: {product.name[:50]}")

            except Exception as e:
                error_msg = f"Ошибка добавления {product_data.get('article_code')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue

        result_message = f"Добавлено {added_count} новых товаров"
        if updated_count > 0:
            result_message += f", обновлено: {updated_count}"
        if errors:
            result_message += f", ошибок: {len(errors)}"

        return {
            'success': True,
            'message': result_message,
            'added': added_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors[:5]  # Первые 5 ошибок
        }

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {
            'success': False,
            'message': 'Пользователь не найден'
        }
    except Exception as e:
        logger.error(f"Error adding items from catalog: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Ошибка при добавлении товаров: {str(e)}'
        }


@shared_task
def cleanup_old_price_history():
    """Удалить старую историю цен (старше 90 дней)"""
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=90)
    deleted = PriceHistory.objects.filter(checked_at__lt=cutoff_date).delete()

    logger.info(f"Deleted {deleted[0]} old price history records")
    return f"Deleted {deleted[0]} old price history records"


@shared_task
def import_favorites_from_wildberries(user_id):
    """
    Импорт товаров из избранного Wildberries

    Args:
        user_id: ID пользователя Django

    Returns:
        dict: {'success': bool, 'imported': int, 'failed': int, 'message': str}
    """
    from .selenium_parser import parse_favorites_with_selenium
    import time

    logger.info(f"Начинаю импорт избранного для пользователя {user_id}")

    try:
        # В Docker/production Selenium всегда headless — нет дисплея.
        # Для локального запуска с браузером установите SELENIUM_HEADLESS=False.
        import os
        headless_mode = os.environ.get('SELENIUM_HEADLESS', 'True').lower() != 'false'
        product_urls = parse_favorites_with_selenium(
            user_id=user_id,
            headless=headless_mode,
            max_items=200
        )

        if not product_urls:
            return {
                'success': False,
                'imported': 0,
                'failed': 0,
                'message': 'Не удалось получить товары из избранного. Возможно, требуется авторизация.'
            }

        logger.info(f"Получено {len(product_urls)} товаров из избранного")

        imported_count = 0
        failed_count = 0
        errors = []

        # Добавляем каждый товар через существующую функцию
        for url in product_urls:
            try:
                result = add_item_by_url_task(user_id, url)

                if result.get('success'):
                    imported_count += 1
                    logger.info(f"✅ Импортирован: {url}")
                else:
                    failed_count += 1
                    error_msg = result.get('message', 'Неизвестная ошибка')
                    if 'уже в вашем списке' not in error_msg:  # Игнорируем дубликаты
                        errors.append(f"{url}: {error_msg}")
                    logger.warning(f"⚠️ Не удалось импортировать: {url} - {error_msg}")

                # Небольшая пауза между запросами
                time.sleep(1)

            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                errors.append(f"{url}: {error_msg}")
                logger.error(f"❌ Ошибка при импорте {url}: {e}")

        # Формируем итоговое сообщение
        message = f"Импортировано: {imported_count}, Не удалось: {failed_count}"
        if errors and len(errors) <= 5:
            message += f"\nОшибки: {'; '.join(errors[:5])}"

        logger.info(f"✅ Импорт завершен: {message}")

        return {
            'success': True,
            'imported': imported_count,
            'failed': failed_count,
            'message': message
        }

    except Exception as e:
        error_msg = f"Ошибка при импорте избранного: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'imported': 0,
            'failed': 0,
            'message': error_msg
        }




@shared_task(bind=True)
def import_favorites_from_text(self, user_id, raw_data):
    """
    Массовый импорт WB-товаров из сырого текста (формат "название + ссылка")

    Args:
        user_id: ID пользователя Django
        raw_data: Сырой текст со списком товаров

    Returns:
        dict: {'success': bool, 'imported': int, 'failed': int, 'message': str}
    """
    import time

    logger.info(f"Начинаю массовый импорт избранного из текста для пользователя {user_id}")

    run = None

    try:
        user = User.objects.get(id=user_id)
        total_start_ts = time.perf_counter()
        entries = _extract_wb_entries_from_raw_data(raw_data)

        if not entries:
            return {
                'success': False,
                'imported': 0,
                'failed': 0,
                'message': 'Не удалось найти корректные ссылки Wildberries во входном тексте.'
            }

        logger.info(f"Найдено {len(entries)} товаров WB для быстрого импорта")

        total_entries = len(entries)
        run = ImportRun.objects.create(
            user=user,
            source='wb_share_text',
            status='running',
            total_links=total_entries,
        )
        fast_start_ts = time.perf_counter()

        imported_count = 0
        failed_count = 0
        skipped_duplicates = 0
        skipped_fresh_enrich = 0
        created_count = 0
        reactivated_count = 0
        errors = []
        article_codes_for_enrich = []

        self.update_state(
            state='STARTED',
            meta={
                'success': True,
                'stage': 'fast_import',
                'processed': 0,
                'total': total_entries,
                'created': created_count,
                'reactivated': reactivated_count,
                'duplicates': skipped_duplicates,
                'failed': failed_count,
                'message': f'Импорт ссылок: 0/{total_entries}'
            }
        )

        for index, entry in enumerate(entries, start=1):
            article_code = entry.get('article_code')
            url = entry.get('url')
            name = (entry.get('name') or '').strip()

            try:
                # Этап 1: мгновенное создание/обновление Product без Selenium
                product, created = Product.objects.get_or_create(
                    article_code=article_code,
                    defaults={
                        'name': name or f"Товар {article_code}",
                        'marketplace': 'wildberries',
                        'url': url,
                        'image_url': _build_wb_default_image_url(article_code),
                    }
                )

                if not created:
                    fields_to_update = []
                    if url and product.url != url:
                        product.url = url
                        fields_to_update.append('url')
                    if name and (not product.name or product.name.startswith('Товар ')):
                        product.name = name
                        fields_to_update.append('name')
                    if not product.image_url:
                        product.image_url = _build_wb_default_image_url(article_code)
                        fields_to_update.append('image_url')
                    if fields_to_update:
                        product.save(update_fields=fields_to_update)

                # Этап 1: мгновенно добавляем/восстанавливаем в wishlist
                existing_item = Item.objects.filter(user=user, product=product).first()
                if existing_item:
                    if not existing_item.is_active:
                        existing_item.is_active = True
                        existing_item.save(update_fields=['is_active'])
                        imported_count += 1
                        reactivated_count += 1
                    else:
                        skipped_duplicates += 1
                else:
                    Item.objects.create(user=user, product=product)
                    imported_count += 1
                    created_count += 1

                # Этап 2: фоновое обогащение запускаем только если данные устарели/неполные
                if _product_needs_enrichment(product):
                    article_codes_for_enrich.append(article_code)
                else:
                    skipped_fresh_enrich += 1

            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                errors.append(f"{article_code or url}: {error_msg}")
                logger.error(f"❌ Ошибка при импорте {url}: {e}")

            self.update_state(
                state='STARTED',
                meta={
                    'success': True,
                    'stage': 'fast_import',
                    'processed': index,
                    'total': total_entries,
                    'created': created_count,
                    'reactivated': reactivated_count,
                    'duplicates': skipped_duplicates,
                    'failed': failed_count,
                    'message': f'Импорт ссылок: {index}/{total_entries}'
                }
            )

        enrich_task_id = None
        if article_codes_for_enrich:
            unique_codes = list(dict.fromkeys(article_codes_for_enrich))
            enrich_task = enrich_wb_products_batch.delay(unique_codes, run.id)
            enrich_task_id = enrich_task.id

        fast_import_ms = int((time.perf_counter() - fast_start_ts) * 1000)

        message = (
            f"Импортировано: {imported_count}, "
            f"Создано: {created_count}, "
            f"Восстановлено: {reactivated_count}, "
            f"Пропущено обогащение (данные свежие): {skipped_fresh_enrich}, "
            f"Дубликаты: {skipped_duplicates}, "
            f"Ошибки: {failed_count}, "
            f"Всего ссылок: {len(entries)}"
        )
        if enrich_task_id:
            message += f". Обогащение данных запущено в фоне (task_id: {enrich_task_id})"
        if errors and len(errors) <= 5:
            message += f"\nОшибки: {'; '.join(errors[:5])}"

        logger.info(f"✅ Массовый импорт завершен: {message}")

        run.imported_count = imported_count
        run.created_count = created_count
        run.reactivated_count = reactivated_count
        run.duplicates_count = skipped_duplicates
        run.failed_count = failed_count
        run.fast_import_ms = fast_import_ms
        run.enrich_task_id = enrich_task_id
        run.message = message
        run.sample_errors = errors[:10]

        if enrich_task_id:
            run.status = 'enriching'
        else:
            run.status = 'completed'
            run.finished_at = timezone.now()
            run.total_ms = int((time.perf_counter() - total_start_ts) * 1000)

        run.save()

        return {
            'success': True,
            'imported': imported_count,
            'failed': failed_count,
            'duplicates': skipped_duplicates,
            'created': created_count,
            'reactivated': reactivated_count,
            'enrich_task_id': enrich_task_id,
            'run_id': run.id,
            'fast_import_ms': fast_import_ms,
            'sample_errors': errors[:10],
            'message': message
        }

    except Exception as e:
        error_msg = f"Ошибка при массовом импорте из текста: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if run is not None:
            run.status = 'failed'
            run.finished_at = timezone.now()
            run.message = error_msg
            run.save(update_fields=['status', 'finished_at', 'message'])
        return {
            'success': False,
            'imported': 0,
            'failed': 0,
            'message': error_msg
        }


@shared_task(bind=True)
def enrich_wb_products_batch(self, article_codes, import_run_id=None):
    """
    Обогащает WB товары в 1 Selenium-сессии на весь batch.

    Это и есть ускорение: не поднимаем новый браузер для каждого товара.
    """
    import time
    from .selenium_parser import SeleniumWildberriesParser

    if not article_codes:
        return {
            'success': True,
            'updated': 0,
            'failed': 0,
            'message': 'Нет товаров для обогащения'
        }

    updated_count = 0
    failed_count = 0
    selenium_enriched_count = 0
    enrich_start_ts = time.perf_counter()

    products_queryset = Product.objects.filter(
        marketplace='wildberries',
        article_code__in=article_codes,
    )
    products = [product for product in products_queryset if _product_needs_enrichment(product)]
    total_products = len(products)

    if total_products == 0:
        if import_run_id:
            try:
                run = ImportRun.objects.get(id=import_run_id)
                run.status = 'completed'
                run.finished_at = timezone.now()
                run.enrich_api_ms = 0
                run.enrich_selenium_ms = 0
                run.total_ms = run.fast_import_ms or 0
                run.message = run.message + " | Обогащение пропущено: данные актуальны"
                run.save(update_fields=['status', 'finished_at', 'enrich_api_ms', 'enrich_selenium_ms', 'total_ms', 'message'])
            except ImportRun.DoesNotExist:
                logger.warning(f"ImportRun {import_run_id} не найден для обновления метрик")

        return {
            'success': True,
            'stage': 'enrich',
            'processed': 0,
            'total': 0,
            'updated': 0,
            'api_enriched': 0,
            'selenium_enriched': 0,
            'enrich_api_ms': 0,
            'enrich_selenium_ms': 0,
            'total_enrich_ms': 0,
            'failed': 0,
            'message': 'Обогащение пропущено: данные товаров актуальны'
        }

    self.update_state(
        state='STARTED',
        meta={
            'success': True,
            'stage': 'enrich',
            'processed': 0,
            'total': total_products,
            'updated': updated_count,
            'failed': failed_count,
            'message': f'Обогащение товаров: 0/{total_products}'
        }
    )
    enrich_api_ms = 0
    selenium_phase_start_ts = time.perf_counter()

    with SeleniumWildberriesParser(headless=True) as parser:
        selenium_total = total_products
        for index, product in enumerate(products, start=1):
            try:
                product_url = product.url or f"https://www.wildberries.ru/catalog/{product.article_code}/detail.aspx"
                cache_key = _parsed_product_cache_key('wildberries', article_code=product.article_code, url=product_url)
                parsed = cache.get(cache_key)
                if not parsed:
                    parsed = parser.parse(product_url, timeout=25)
                    if parsed:
                        cache.set(cache_key, parsed, timeout=PARSED_PRODUCT_CACHE_TTL)
                if not parsed:
                    failed_count += 1
                    continue

                changed_fields = []

                if parsed.get('name'):
                    product.name = parsed.get('name')
                    changed_fields.append('name')
                if parsed.get('price') is not None:
                    product.price = _to_decimal_or_none(parsed.get('price'))
                    changed_fields.append('price')
                if parsed.get('image_url'):
                    product.image_url = parsed.get('image_url')
                    changed_fields.append('image_url')
                if parsed.get('brand'):
                    product.brand = parsed.get('brand')
                    changed_fields.append('brand')
                if parsed.get('category'):
                    product.category = parsed.get('category')
                    changed_fields.append('category')

                parsed_rating = _to_decimal_or_none(parsed.get('rating'))
                if parsed_rating is not None:
                    product.rating = parsed_rating
                    changed_fields.append('rating')

                parsed_reviews = _to_int_or_none(parsed.get('reviews_count'))
                if parsed_reviews is not None:
                    product.reviews_count = parsed_reviews
                    changed_fields.append('reviews_count')

                if changed_fields:
                    product.last_price_check = timezone.now()
                    changed_fields.append('last_price_check')
                    product.save(update_fields=list(dict.fromkeys(changed_fields)))
                    updated_count += 1
                    selenium_enriched_count += 1

            except Exception as enrich_error:
                failed_count += 1
                logger.warning(
                    f"Не удалось обогатить товар {product.article_code}: {enrich_error}"
                )

            self.update_state(
                state='STARTED',
                meta={
                    'success': True,
                    'stage': 'enrich',
                    'phase': 'selenium',
                    'processed': index,
                    'total': selenium_total,
                    'updated': updated_count,
                    'api_enriched': 0,
                    'selenium_enriched': selenium_enriched_count,
                    'failed': failed_count,
                    'message': f'Selenium: {index}/{selenium_total}'
                }
            )

    enrich_selenium_ms = int((time.perf_counter() - selenium_phase_start_ts) * 1000)
    total_enrich_ms = int((time.perf_counter() - enrich_start_ts) * 1000)

    if import_run_id:
        try:
            run = ImportRun.objects.get(id=import_run_id)
            run.status = 'completed'
            run.finished_at = timezone.now()
            run.api_enriched_count = 0
            run.selenium_enriched_count = selenium_enriched_count
            run.enrich_api_ms = enrich_api_ms
            run.enrich_selenium_ms = enrich_selenium_ms
            run.total_ms = (run.fast_import_ms or 0) + total_enrich_ms
            run.message = (
                run.message +
                f" | Обогащение: Selenium {selenium_enriched_count}, Ошибок {failed_count}"
            )
            run.save()
        except ImportRun.DoesNotExist:
            logger.warning(f"ImportRun {import_run_id} не найден для обновления метрик")

    return {
        'success': True,
        'stage': 'enrich',
        'processed': total_products,
        'total': total_products,
        'updated': updated_count,
        'api_enriched': 0,
        'selenium_enriched': selenium_enriched_count,
        'enrich_api_ms': enrich_api_ms,
        'enrich_selenium_ms': enrich_selenium_ms,
        'total_enrich_ms': total_enrich_ms,
        'failed': failed_count,
        'message': (
            f'Обогащено: {updated_count} '
            f'(Selenium: {selenium_enriched_count}), '
            f'Ошибок: {failed_count}'
        )
    }
