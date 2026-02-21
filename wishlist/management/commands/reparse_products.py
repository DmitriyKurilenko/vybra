"""
Команда для перепарсинга товаров с неправильными названиями
"""
from django.core.management.base import BaseCommand
from wishlist.models import Product
import re
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Перепарсить товары с названиями "Товар {артикул}"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать товары без перепарсинга',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Максимальное количество товаров для перепарсинга',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        # Находим товары с названиями в формате "Товар {артикул}"
        products = Product.objects.filter(name__startswith='Товар ')

        # Фильтруем только те, где название точно в формате "Товар {число}"
        products_to_reparse = []
        for product in products:
            if re.match(r'^Товар \d+$', product.name):
                products_to_reparse.append(product)

        if not products_to_reparse:
            self.stdout.write(self.style.SUCCESS('Нет товаров для перепарсинга'))
            return

        self.stdout.write(
            self.style.WARNING(f'Найдено {len(products_to_reparse)} товаров с неправильными названиями')
        )

        if dry_run:
            self.stdout.write(self.style.NOTICE('Режим dry-run, перепарсинг не выполняется'))
            for product in products_to_reparse[:10]:
                self.stdout.write(f'  - {product.name} (артикул: {product.article_code})')
            if len(products_to_reparse) > 10:
                self.stdout.write(f'  ... и еще {len(products_to_reparse) - 10} товаров')
            return

        # Ограничиваем количество если задан limit
        if limit:
            products_to_reparse = products_to_reparse[:limit]
            self.stdout.write(self.style.NOTICE(f'Обрабатываю первые {limit} товаров'))

        # Перепарсиваем каждый товар
        success_count = 0
        error_count = 0

        for i, product in enumerate(products_to_reparse, 1):
            try:
                self.stdout.write(f'[{i}/{len(products_to_reparse)}] Парсинг: {product.name}...')

                # Формируем URL товара
                url = None
                if product.url:
                    url = product.url
                elif product.marketplace == 'wildberries' and product.article_code:
                    url = f'https://www.wildberries.ru/catalog/{product.article_code}/detail.aspx'

                if not url:
                    self.stdout.write(self.style.ERROR(f'  ❌ Нет URL для товара {product.id}'))
                    error_count += 1
                    continue

                # Парсим товар
                if product.marketplace == 'wildberries':
                    from wishlist.selenium_parser import parse_with_selenium
                    result = parse_with_selenium(url, headless=True)
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  Пропускаю {product.marketplace}'))
                    continue

                if not result or not result.get('name'):
                    self.stdout.write(self.style.ERROR(f'  ❌ Не удалось получить название'))
                    error_count += 1
                    continue

                # Обновляем название
                old_name = product.name
                product.name = result['name']

                # Обновляем другие данные если они есть
                if result.get('price'):
                    product.price = result['price']
                if result.get('image_url'):
                    product.image_url = result['image_url']

                product.save()

                self.stdout.write(
                    self.style.SUCCESS(f'  ✅ {old_name} → {product.name[:50]}...')
                )
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Ошибка: {e}'))
                logger.error(f'Ошибка перепарсинга товара {product.id}: {e}', exc_info=True)
                error_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Успешно обновлено: {success_count}'))
        if error_count:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {error_count}'))
