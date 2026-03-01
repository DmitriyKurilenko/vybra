"""
Management command для создания тестовых пользователей и админа
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
from decimal import Decimal
from wishlist.models import Product, Item
import random


class Command(BaseCommand):
    help = 'Создает/обновляет тестовых пользователей, админа и тестовые данные'

    TEST_ACCOUNTS = [
        {
            'username': 'admin',
            'email': 'admin@prvms.ru',
            'password': 'test123',
            'is_staff': True,
            'is_superuser': True,
        },
        {
            'username': 'demo',
            'email': 'demo@prvms.ru',
            'password': 'test123',
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'username': 'test1',
            'email': 'test1@prvms.ru',
            'password': 'test123',
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'username': 'test2',
            'email': 'test2@prvms.ru',
            'password': 'test123',
            'is_staff': False,
            'is_superuser': False,
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Не создавать тестовые товары для пользователей',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Перезаписать существующих пользователей (email/username/пароль/права)',
        )

    def _find_user(self, email: str, username: str):
        matches = list(
            User.objects.filter(
                Q(email__iexact=email) | Q(username=username)
            ).order_by('id')
        )
        if not matches:
            return None
        exact_email = next((user for user in matches if (user.email or '').lower() == email.lower()), None)
        return exact_email or matches[0]

    def _create_or_update_account(self, account: dict, overwrite: bool):
        username = account['username']
        email = account['email'].strip().lower()
        password = account['password']
        is_staff = bool(account.get('is_staff', False))
        is_superuser = bool(account.get('is_superuser', False))

        user = self._find_user(email=email, username=username)
        if user is None:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.is_active = True
            user.save()
            return user, 'created'

        if not overwrite:
            return user, 'skipped'

        user.username = username
        user.email = email
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = True
        user.set_password(password)
        user.save()
        return user, 'updated'

    def handle(self, *args, **options):
        overwrite = bool(options.get('overwrite'))
        mode_label = 'с перезаписью' if overwrite else 'без перезаписи'
        self.stdout.write(self.style.SUCCESS(f'Создание тестовых пользователей ({mode_label})...'))

        created_users = []
        for account in self.TEST_ACCOUNTS:
            user, status = self._create_or_update_account(account, overwrite=overwrite)
            created_users.append(user)

            if status == 'created':
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Создан пользователь: {account["email"]}')
                )
            elif status == 'updated':
                self.stdout.write(
                    self.style.SUCCESS(f'♻️  Обновлен пользователь: {account["email"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Пользователь уже существует: {account["email"]} '
                        '(используйте --overwrite для перезаписи)'
                    )
                )

        # Создать тестовые товары для demo пользователя
        if not options['skip_products'] and created_users:
            demo_email = next(acc['email'] for acc in self.TEST_ACCOUNTS if acc['username'] == 'demo')
            try:
                demo_user = User.objects.get(email__iexact=demo_email)
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
        self.stdout.write(self.style.WARNING('\nДоступные учетные записи:'))
        for account in self.TEST_ACCOUNTS:
            role = 'Админ' if account.get('is_superuser') else 'Польз.'
            self.stdout.write(
                f'  {role}: {account["email"]:<20} | Пароль: {account["password"]}'
            )
        self.stdout.write('\n' + '='*60 + '\n')
