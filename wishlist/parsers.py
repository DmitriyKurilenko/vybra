"""
Парсеры для маркетплейсов
Поддержка: Wildberries, Ozon
"""
import requests
import re
import os
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class MarketplaceParser:
    """Базовый класс для парсеров маркетплейсов"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        })

    def parse(self, url: str) -> Optional[Dict]:
        """
        Парсинг товара по URL

        Returns:
            Dict с полями: price, name, image_url, rating, или None
        """
        raise NotImplementedError


class WildberriesParser(MarketplaceParser):
    """Парсер для Wildberries через публичное API"""

    def __init__(self):
        super().__init__()
        self._selenium_parser = None
        self._selenium_timeout = max(5, int(os.environ.get('WB_SELENIUM_FALLBACK_TIMEOUT', '20')))
        self._selenium_retries = max(1, int(os.environ.get('WB_SELENIUM_FALLBACK_RETRIES', '1')))
        self.session.headers.update({
            'Origin': 'https://www.wildberries.ru',
            'Referer': 'https://www.wildberries.ru/',
        })

    def _get_selenium_parser(self):
        if self._selenium_parser is None:
            from .selenium_parser import SeleniumWildberriesParser
            self._selenium_parser = SeleniumWildberriesParser(headless=True)
        return self._selenium_parser

    def close(self):
        if self._selenium_parser:
            try:
                self._selenium_parser.close()
            except Exception:
                pass
            self._selenium_parser = None

    def __del__(self):
        self.close()

    def extract_product_id(self, url: str) -> Optional[str]:
        """Извлечь ID товара из URL"""
        patterns = [
            r'/catalog/(\d+)/',
            r'/(\d+)/detail',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def parse(self, url: str) -> Optional[Dict]:
        """
        Парсинг товара Wildberries

        Использует публичное API для получения данных.
        Если товар недоступен через API, возвращает None.
        """
        product_id = self.extract_product_id(url)
        if not product_id:
            logger.warning(f"Cannot extract product ID from URL: {url}")
            return None

        # Пробуем разные API endpoints с разными регионами
        api_configs = [
            {
                'url': 'https://card.wb.ru/cards/v2/detail',
                'params': {
                    'appType': 1,
                    'curr': 'rub',
                    'dest': -1257786,  # Москва
                    'spp': 30,
                    'nm': product_id
                }
            },
            {
                'url': 'https://card.wb.ru/cards/v2/detail',
                'params': {
                    'appType': 1,
                    'curr': 'rub',
                    'dest': -1181464,  # Санкт-Петербург
                    'spp': 30,
                    'nm': product_id
                }
            },
            {
                'url': 'https://card.wb.ru/cards/detail',
                'params': {
                    'appType': 1,
                    'curr': 'rub',
                    'dest': -1257786,
                    'spp': 30,
                    'nm': product_id
                }
            },
        ]

        for config in api_configs:
            try:
                response = self.session.get(
                    config['url'],
                    params=config['params'],
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    result = self._parse_api_response(data)
                    if result:
                        logger.info(f"Successfully parsed WB product {product_id}")
                        return result

            except requests.RequestException as e:
                logger.debug(f"API request failed: {e}")
                continue
            except (ValueError, KeyError) as e:
                logger.debug(f"Failed to parse API response: {e}")
                continue

        logger.warning(f"Failed to fetch WB product {product_id} from all API endpoints")

        # Fallback: Пробуем Selenium если API не работает
        logger.info(f"Trying Selenium parser as fallback for {product_id}")
        try:
            result = self._get_selenium_parser().parse(
                url,
                timeout=self._selenium_timeout,
                retries=self._selenium_retries,
            )
            if result:
                logger.info(f"Successfully parsed WB product {product_id} via Selenium")
                return result
        except ImportError:
            logger.warning("Selenium not available (not installed)")
        except Exception as e:
            logger.error(f"Selenium parser failed: {e}")

        return None

    def _parse_api_response(self, data: Dict) -> Optional[Dict]:
        """Парсинг ответа API Wildberries"""
        try:
            # Проверяем разные структуры ответа
            products = None
            if 'data' in data and 'products' in data['data']:
                products = data['data']['products']
            elif 'data' in data and 'cards' in data['data']:
                products = data['data']['cards']

            if not products or len(products) == 0:
                return None

            product = products[0]

            result = {
                'name': product.get('name'),
                'price': None,
                'old_price': None,
                'image_url': None,
                'rating': product.get('reviewRating'),
            }

            # Цена (в API указана в копейках, умножена на 100)
            if 'salePriceU' in product and product['salePriceU']:
                try:
                    result['price'] = Decimal(product['salePriceU']) / 100
                except (InvalidOperation, TypeError):
                    pass

            if 'priceU' in product and product['priceU']:
                try:
                    result['old_price'] = Decimal(product['priceU']) / 100
                except (InvalidOperation, TypeError):
                    pass

            # URL изображения
            if 'id' in product:
                vol = product['id'] // 100000
                part = product['id'] // 1000
                result['image_url'] = (
                    f"https://basket-{vol:02d}.wbbasket.ru/vol{vol}/part{part}/"
                    f"{product['id']}/images/c516x688/1.webp"
                )

            # Возвращаем только если есть хотя бы цена
            if result['price'] is not None:
                return result

        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"Error parsing WB API response: {e}")

        return None


class OzonParser(MarketplaceParser):
    """Парсер для Ozon"""

    def extract_product_id(self, url: str) -> Optional[str]:
        """Извлечь ID товара из URL Ozon"""
        # Пример: https://www.ozon.ru/product/name-123456789/
        patterns = [
            r'/product/[^/]+-(\d+)/',
            r'-(\d+)/$',
            r'-(\d+)\?',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def parse(self, url: str) -> Optional[Dict]:
        """
        Парсинг товара Ozon

        Примечание: Ozon также использует антибот-защиту.
        Для продакшена рекомендуется использовать:
        1. Selenium/Playwright
        2. Официальное API Ozon (требует регистрации)
        3. Платные сервисы парсинга
        """
        product_id = self.extract_product_id(url)
        if not product_id:
            logger.warning(f"Cannot extract product ID from Ozon URL: {url}")
            return None

        # TODO: Реализовать парсинг Ozon
        # Варианты:
        # 1. API endpoint (если найдем публичный)
        # 2. Selenium для обхода защиты
        # 3. Официальное API (требует ключи)

        logger.warning("Ozon parser not fully implemented yet")
        return None


def get_parser(marketplace: str) -> Optional[MarketplaceParser]:
    """
    Фабрика парсеров

    Args:
        marketplace: 'wildberries', 'ozon', или 'other'

    Returns:
        Экземпляр парсера или None
    """
    parsers = {
        'wildberries': WildberriesParser,
        'ozon': OzonParser,
    }

    parser_class = parsers.get(marketplace.lower())
    if parser_class:
        return parser_class()

    logger.warning(f"No parser available for marketplace: {marketplace}")
    return None


def fetch_price(url: str, marketplace: str) -> Optional[Decimal]:
    """
    Получить цену товара по URL

    Эта функция используется в Celery tasks для обновления цен.

    Args:
        url: URL товара
        marketplace: Название маркетплейса

    Returns:
        Decimal цена или None при ошибке
    """
    parser = get_parser(marketplace)
    if not parser:
        return None

    try:
        result = parser.parse(url)
        if result and result.get('price'):
            return result['price']
    except Exception as e:
        logger.error(f"Error fetching price from {marketplace}: {e}")

    return None
