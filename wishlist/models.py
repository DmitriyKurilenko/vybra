from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.validators import URLValidator


class Product(models.Model):
    """Глобальный каталог товаров из всех маркетплейсов"""

    MARKETPLACE_CHOICES = [
        ('ozon', 'Ozon'),
        ('wildberries', 'Wildberries'),
        ('other', 'Другое'),
    ]

    article_code = models.CharField(max_length=100, unique=True, db_index=True, verbose_name='Артикул')
    name = models.CharField(max_length=500, verbose_name='Название')
    marketplace = models.CharField(max_length=20, choices=MARKETPLACE_CHOICES, db_index=True)
    url = models.URLField(max_length=1000, validators=[URLValidator()], blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True, verbose_name='Бренд')
    category = models.CharField(max_length=300, blank=True, null=True, verbose_name='Категория')
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, verbose_name='Рейтинг')
    reviews_count = models.IntegerField(null=True, blank=True, verbose_name='Количество отзывов')

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True, verbose_name='Первое обнаружение')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')
    last_price_check = models.DateTimeField(null=True, blank=True, verbose_name='Последняя проверка цены')

    class Meta:
        ordering = ['-last_updated']
        verbose_name = 'Товар в каталоге'
        verbose_name_plural = 'Товары в каталоге'
        indexes = [
            models.Index(fields=['marketplace', 'article_code']),
            models.Index(fields=['-last_updated']),
            models.Index(fields=['category', 'price']),
            models.Index(fields=['price']),
            models.Index(fields=['category']),
            models.Index(fields=['price'], condition=Q(price__isnull=False), name='wishlist_pr_valid_price_idx'),
        ]

    def __str__(self):
        return f"{self.article_code}: {self.name}"


class Item(models.Model):
    """Товар в wishlist пользователя (ссылка на Product)"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')

    # ELO rating system
    elo_rating = models.IntegerField(default=1500, db_index=True)
    comparisons_count = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)

    # Metadata
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-elo_rating', '-added_at']
        verbose_name = 'Товар в wishlist'
        verbose_name_plural = 'Товары в wishlist'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'is_active', '-elo_rating']),
            models.Index(fields=['user', 'added_at']),
            models.Index(fields=['user', 'comparisons_count']),
        ]

    def __str__(self):
        return f"{self.product.name} ({self.elo_rating})"
    
    def calculate_elo_change(self, opponent_rating, won):
        """
        Рассчитать изменение ELO рейтинга с адаптивным K-фактором

        K-фактор зависит от количества сравнений:
        - < 5 сравнений: K=64 (быстрая стабилизация новых товаров)
        - 5-19 сравнений: K=32 (средняя скорость изменения)
        - >= 20 сравнений: K=16 (устоявшийся рейтинг)
        """
        # Адаптивный K-фактор
        if self.comparisons_count < 5:
            K = 64  # Новые товары быстро находят свое место
        elif self.comparisons_count < 20:
            K = 32  # Средняя стабилизация
        else:
            K = 16  # Устоявшийся рейтинг меняется медленно

        expected = 1 / (1 + 10 ** ((opponent_rating - self.elo_rating) / 400))
        actual = 1 if won else 0
        return int(K * (actual - expected))
    
    def update_elo(self, opponent, won):
        """Обновить ELO рейтинг после сравнения.
        Сохраняем только ELO-поля — не все поля объекта."""
        change = self.calculate_elo_change(opponent.elo_rating, won)
        self.elo_rating += change
        self.comparisons_count += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        self.save(update_fields=['elo_rating', 'comparisons_count', 'wins', 'losses'])

    @property
    def confidence(self):
        """
        Уверенность в рейтинге (0-100%)

        Основана на количестве сравнений:
        - 0-2: очень низкая (20-40%)
        - 3-5: низкая (40-60%)
        - 6-10: средняя (60-80%)
        - 11-20: высокая (80-95%)
        - 20+: очень высокая (95-100%)
        """
        if self.comparisons_count == 0:
            return 20
        elif self.comparisons_count <= 2:
            return 20 + (self.comparisons_count * 10)
        elif self.comparisons_count <= 5:
            return 40 + ((self.comparisons_count - 2) * 7)
        elif self.comparisons_count <= 10:
            return 60 + ((self.comparisons_count - 5) * 4)
        elif self.comparisons_count <= 20:
            return int(80 + ((self.comparisons_count - 10) * 1.5))
        else:
            return int(min(100, 95 + (self.comparisons_count - 20) * 0.25))

    @property
    def confidence_level(self):
        """Текстовое описание уверенности"""
        conf = self.confidence
        if conf < 40:
            return "very_low"
        elif conf < 60:
            return "low"
        elif conf < 80:
            return "medium"
        elif conf < 95:
            return "high"
        else:
            return "very_high"


class Comparison(models.Model):
    """История сравнений товаров"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comparisons')
    item1 = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='comparisons_as_item1')
    item2 = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='comparisons_as_item2')
    winner = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='won_comparisons')
    
    # ELO ratings at the time of comparison
    item1_rating_before = models.IntegerField()
    item2_rating_before = models.IntegerField()
    item1_rating_after = models.IntegerField()
    item2_rating_after = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сравнение'
        verbose_name_plural = 'Сравнения'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.item1.product.name} vs {self.item2.product.name} -> {self.winner.product.name}"


class PriceHistory(models.Model):
    """История изменения цен товаров"""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at']
        verbose_name = 'История цены'
        verbose_name_plural = 'История цен'
        indexes = [
            models.Index(fields=['product', '-checked_at']),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.price} руб. ({self.checked_at.strftime('%Y-%m-%d %H:%M')})"


class ImportRun(models.Model):
    """История запусков импорта избранного с техническими метриками"""

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('enriching', 'Enriching'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    SOURCE_CHOICES = [
        ('wb_share_text', 'WB Share Text'),
        ('wb_selenium_favorites', 'WB Selenium Favorites'),
        ('ozon_selenium_favorites', 'Ozon Selenium Favorites'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='import_runs')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='wb_share_text')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', db_index=True)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    total_links = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    reactivated_count = models.IntegerField(default=0)
    duplicates_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    enrich_task_id = models.CharField(max_length=100, null=True, blank=True)
    api_enriched_count = models.IntegerField(default=0)
    selenium_enriched_count = models.IntegerField(default=0)

    fast_import_ms = models.IntegerField(null=True, blank=True)
    enrich_api_ms = models.IntegerField(null=True, blank=True)
    enrich_selenium_ms = models.IntegerField(null=True, blank=True)
    total_ms = models.IntegerField(null=True, blank=True)

    message = models.TextField(blank=True, default='')
    sample_errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        return f"ImportRun #{self.id} ({self.status}) user={self.user_id}"
