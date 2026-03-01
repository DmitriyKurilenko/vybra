"""
Management command для удаления всех товаров из каталога.
"""
from django.core.management.base import BaseCommand
from wishlist.models import Product, Item


class Command(BaseCommand):
    help = 'Удаляет все товары из каталога (Product). Связанные Item удаляются каскадно.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--items-only',
            action='store_true',
            help='Удалить только товары пользователей (Item), не трогая каталог Product',
        )

    def handle(self, *args, **options):
        items_only = bool(options.get('items_only'))

        if items_only:
            items_count = Item.objects.count()
            Item.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Удалены товары пользователей: Item={items_count}')
            )
            return

        products_count = Product.objects.count()
        items_count = Item.objects.count()
        Product.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Удален каталог товаров: Product={products_count}, Item(каскад)={items_count}'
            )
        )
