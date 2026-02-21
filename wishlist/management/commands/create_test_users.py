"""
Management command для создания тестовых пользователей и админа
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from wishlist.models import Product, Item
import random


class Command(BaseCommand):
    help = 'Создает тестовых пользователей, админа и тестовые данные'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Не создавать тестовые товары для пользователей',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Создание тестовых пользователей...'))

        # Создать админа
        admin_email = 'admin@vybra.com'
        if not User.objects.filter(email=admin_email).exists():
            admin = User.objects.create_superuser(
                username='admin',
                email=admin_email,
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Создан админ: {admin.email} / admin123'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Админ уже существует: {admin_email}'))

        # Создать тестовых пользователей
        test_users = [
            {'username': 'demo', 'email': 'demo@vybra.com', 'password': 'demo123'},
            {'username': 'test1', 'email': 'test1@vybra.com', 'password': 'test123'},
            {'username': 'test2', 'email': 'test2@vybra.com', 'password': 'test123'},
        ]

        created_users = []
        for user_data in test_users:
            # Проверяем и по email, и по username
            if not User.objects.filter(email=user_data['email']).exists() and \
               not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password']
                )
                created_users.append(user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Создан пользователь: {user.email} / {user_data["password"]}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Пользователь уже существует: {user_data["email"]}')
                )
                # Пытаемся получить по email, если не найден - по username
                try:
                    user = User.objects.get(email=user_data['email'])
                except User.DoesNotExist:
                    user = User.objects.get(username=user_data['username'])
                created_users.append(user)

        # Создать тестовые товары для demo пользователя
        if not options['skip_products'] and created_users:
            try:
                demo_user = User.objects.get(email='demo@vybra.com')
            except User.DoesNotExist:
                # Если demo пользователь не найден, используем первого из созданных
                demo_user = created_users[0] if created_users else None

            if not demo_user:
                self.stdout.write(
                    self.style.WARNING('⚠️  Не удалось найти demo пользователя для создания товаров')
                )
                return

            self.stdout.write(self.style.SUCCESS('\nСоздание тестовых товаров для demo пользователя...'))

            # Проверяем, есть ли уже товары у пользователя
            existing_items_count = Item.objects.filter(user=demo_user).count()

            if existing_items_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  У demo пользователя уже есть {existing_items_count} товаров. Пропускаю создание.'
                    )
                )
            else:
                # Примеры тестовых товаров
                test_products = [
                    {
                        'name': 'Apple iPhone 15 Pro 256GB',
                        'marketplace': 'ozon',
                        'price': Decimal('89990.00'),
                        'brand': 'Apple',
                        'rating': Decimal('4.9'),
                    },
                    {
                        'name': 'Samsung Galaxy S24 Ultra 512GB',
                        'marketplace': 'wildberries',
                        'price': Decimal('99990.00'),
                        'brand': 'Samsung',
                        'rating': Decimal('4.8'),
                    },
                    {
                        'name': 'Sony WH-1000XM5 Наушники',
                        'marketplace': 'ozon',
                        'price': Decimal('29990.00'),
                        'brand': 'Sony',
                        'rating': Decimal('4.9'),
                    },
                    {
                        'name': 'Xiaomi Redmi Note 13 Pro',
                        'marketplace': 'wildberries',
                        'price': Decimal('24990.00'),
                        'brand': 'Xiaomi',
                        'rating': Decimal('4.7'),
                    },
                    {
                        'name': 'MacBook Air M2 13" 256GB',
                        'marketplace': 'ozon',
                        'price': Decimal('119990.00'),
                        'brand': 'Apple',
                        'rating': Decimal('4.9'),
                    },
                    {
                        'name': 'AirPods Pro 2',
                        'marketplace': 'wildberries',
                        'price': Decimal('19990.00'),
                        'brand': 'Apple',
                        'rating': Decimal('4.8'),
                    },
                    {
                        'name': 'iPad Air 5 64GB',
                        'marketplace': 'ozon',
                        'price': Decimal('59990.00'),
                        'brand': 'Apple',
                        'rating': Decimal('4.9'),
                    },
                    {
                        'name': 'JBL Charge 5 Портативная колонка',
                        'marketplace': 'wildberries',
                        'price': Decimal('12990.00'),
                        'brand': 'JBL',
                        'rating': Decimal('4.7'),
                    },
                    {
                        'name': 'Dyson V15 Detect Беспроводной пылесос',
                        'marketplace': 'ozon',
                        'price': Decimal('54990.00'),
                        'brand': 'Dyson',
                        'rating': Decimal('4.8'),
                    },
                    {
                        'name': 'Kindle Paperwhite 11',
                        'marketplace': 'wildberries',
                        'price': Decimal('14990.00'),
                        'brand': 'Amazon',
                        'rating': Decimal('4.8'),
                    },
                ]

                created_items = 0
                for product_data in test_products:
                    # Создаем Product
                    article_code = f"TEST{random.randint(100000, 999999)}"
                    product, _ = Product.objects.get_or_create(
                        article_code=article_code,
                        defaults={
                            'name': product_data['name'],
                            'marketplace': product_data['marketplace'],
                            'price': product_data['price'],
                            'brand': product_data.get('brand'),
                            'rating': product_data.get('rating'),
                        }
                    )

                    # Создаем Item для demo пользователя
                    item = Item.objects.create(
                        user=demo_user,
                        product=product,
                        elo_rating=1500 + random.randint(-200, 200),  # Случайный начальный рейтинг
                    )
                    created_items += 1

                self.stdout.write(
                    self.style.SUCCESS(f'✅ Создано {created_items} тестовых товаров для demo пользователя')
                )

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✅ Тестовые данные успешно созданы!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('\nДоступные учетные записи:')
        self.stdout.write(self.style.WARNING('Админ:'))
        self.stdout.write('  Email: admin@vybra.com')
        self.stdout.write('  Пароль: admin123')
        self.stdout.write(self.style.WARNING('\nТестовые пользователи:'))
        self.stdout.write('  Email: demo@vybra.com   | Пароль: demo123')
        self.stdout.write('  Email: test1@vybra.com  | Пароль: test123')
        self.stdout.write('  Email: test2@vybra.com  | Пароль: test123')
        self.stdout.write('\n' + '='*60 + '\n')
