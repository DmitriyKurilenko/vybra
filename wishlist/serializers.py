"""
Утилиты для сериализации моделей в JSON
"""
from typing import Dict, Optional
from .models import Item, Product


def get_product_url(product: Optional[Product]) -> Optional[str]:
    """Получить URL товара на маркетплейсе"""
    if not product or not product.article_code:
        return None

    if product.marketplace == 'wildberries':
        return f'https://www.wildberries.ru/catalog/{product.article_code}/detail.aspx'
    elif product.marketplace == 'ozon':
        return f'https://www.ozon.ru/product/{product.article_code}/'
    else:
        return product.url


def serialize_item(item: Item) -> Dict:
    """
    Сериализовать Item в словарь для API

    Args:
        item: Объект Item с select_related('product')

    Returns:
        Dict с данными товара
    """
    product = item.product

    return {
        'id': item.id,
        'name': product.name if product else '',
        'article_code': product.article_code if product else None,
        'url': get_product_url(product),
        'marketplace': product.marketplace if product else 'other',
        'category': product.category if product else None,
        'price': float(product.price) if product and product.price else None,
        'image_url': product.image_url if product else None,
        'rating': float(product.rating) if product and product.rating is not None else None,
        'reviews_count': product.reviews_count if product else None,
        'elo_rating': item.elo_rating,
        'comparisons_count': item.comparisons_count,
        'wins': item.wins,
        'losses': item.losses,
        'confidence': item.confidence,
        'confidence_level': item.confidence_level
    }
