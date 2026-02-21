from django.contrib import admin
from .models import Product, Item, Comparison, PriceHistory, ImportRun


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['article_code', 'name', 'marketplace', 'price', 'first_seen', 'last_updated']
    list_filter = ['marketplace', 'first_seen']
    search_fields = ['article_code', 'name', 'brand']
    readonly_fields = ['first_seen', 'last_updated', 'last_price_check']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'product', 'elo_rating', 'comparisons_count', 'added_at']
    list_filter = ['is_active', 'added_at']
    search_fields = ['product__name', 'product__article_code']
    readonly_fields = ['elo_rating', 'comparisons_count', 'wins', 'losses', 'added_at']
    autocomplete_fields = ['product']


@admin.register(Comparison)
class ComparisonAdmin(admin.ModelAdmin):
    list_display = ['user', 'item1', 'item2', 'winner', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'price', 'checked_at']
    list_filter = ['checked_at']
    readonly_fields = ['checked_at']


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'source', 'status', 'total_links',
        'imported_count', 'duplicates_count', 'failed_count',
        'started_at', 'finished_at'
    ]
    list_filter = ['status', 'source', 'started_at']
    search_fields = ['user__username', 'user__email', 'enrich_task_id']
    readonly_fields = [
        'started_at', 'finished_at', 'fast_import_ms', 'enrich_api_ms',
        'enrich_selenium_ms', 'total_ms', 'sample_errors'
    ]
