"""
Wishlist API endpoints - Django Ninja
"""
import logging
import uuid

from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from typing import List
from datetime import timedelta

logger = logging.getLogger(__name__)

from .models import Item, Comparison, PriceHistory, Product, ImportRun
from .serializers import serialize_item
from .ninja_utils import JWTAuth, ValidationError, NotFoundError
from django.contrib.auth.models import User
from .schemas import (
    ItemSchema,
    ItemCreateSchema,
    ItemFromUrlSchema,
    ItemsFromCatalogSchema,
    WBFavoritesImportSchema,
    DashboardSchema,
    DashboardStatsSchema,
    TaskResponseSchema,
    TaskStatusSchema,
    ImportRunSchema,
    ImportMetricsSchema,
    ComparisonSchema,
    ComparisonCreateSchema,
    ComparisonPairSchema,
    PriceHistorySchema,
    StatisticsSchema,
    ProfileSchema,
    ProfileUpdateSchema,
    MessageResponseSchema,
    MessageWithCountSchema,
)


# Router with JWT authentication
router = Router(tags=["Wishlist"])
auth = JWTAuth()


INVALID_PRODUCT_NAME_MARKERS = (
    "по вашему запросу ничего не найдено",
    "ничего не найдено",
    "товар не найден",
)

COMPARE_PAIR_CACHE_TTL = int(getattr(settings, 'COMPARE_PAIR_CACHE_TTL', 20))
COMPARE_PRICE_TOLERANCE = float(getattr(settings, 'COMPARE_PRICE_TOLERANCE', 0.10))


def _pair_cache_key(user_id: int, session_type: str) -> str:
    return f"compare_pair:u{user_id}:{session_type}"


def _normalized_category(value):
    return (value or "").strip().lower()


def _category_match(item_a, item_b):
    category_a = _normalized_category(item_a.product.category if item_a.product else None)
    category_b = _normalized_category(item_b.product.category if item_b.product else None)
    return bool(category_a and category_b and category_a == category_b)


def _price_match(item_a, item_b, tolerance: float = COMPARE_PRICE_TOLERANCE):
    price_a = float(item_a.product.price) if item_a.product and item_a.product.price else None
    price_b = float(item_b.product.price) if item_b.product and item_b.product.price else None
    if not price_a or not price_b or price_a <= 0 or price_b <= 0:
        return False

    min_price = price_a * (1 - tolerance)
    max_price = price_a * (1 + tolerance)
    return min_price <= price_b <= max_price


def _is_valid_for_comparison(item):
    if not item.product:
        return False

    if item.product.price is None or item.product.price <= 0:
        return False

    name = (item.product.name or "").strip().lower()
    if not name:
        return False

    return not any(marker in name for marker in INVALID_PRODUCT_NAME_MARKERS)


def _pick_balanced_pair(items):
    item_list = list(items)
    if len(item_list) < 2:
        return None

    first_item = random.choice(item_list)
    other_items = [item for item in item_list if item.id != first_item.id]

    compatible = [
        item for item in other_items
        if _category_match(first_item, item) or _price_match(first_item, item)
    ]

    if compatible:
        second_item = random.choice(compatible)
        return first_item, second_item

    # Fallback: ближайшая цена, если категорий/диапазона ±10% нет
    first_price = float(first_item.product.price)
    second_item = min(
        other_items,
        key=lambda item: abs(float(item.product.price) - first_price)
    )
    return first_item, second_item


def _load_cached_pair(user, session_type: str, items_by_id: dict):
    cached = cache.get(_pair_cache_key(user.id, session_type))
    if not cached:
        return None

    item1 = items_by_id.get(cached.get('item1_id'))
    item2 = items_by_id.get(cached.get('item2_id'))
    if not item1 or not item2 or item1.id == item2.id:
        return None

    return item1, item2


def _store_cached_pair(user, session_type: str, item1_id: int, item2_id: int):
    cache.set(
        _pair_cache_key(user.id, session_type),
        {'item1_id': item1_id, 'item2_id': item2_id},
        timeout=COMPARE_PAIR_CACHE_TTL,
    )


def _invalidate_pair_cache(user_id: int):
    for session_type in ('all', 'top50', 'bottom50'):
        cache.delete(_pair_cache_key(user_id, session_type))


# ============================================================================
# ITEMS ENDPOINTS
# ============================================================================

@router.get("/items", response=List[ItemSchema], auth=auth)
def list_items(request):
    """Получить все товары пользователя"""
    items = Item.objects.filter(
        user=request.auth,
        is_active=True
    ).select_related('product')
    return [serialize_item(item) for item in items]


@router.get("/items/top", response=List[ItemSchema], auth=auth)
def top_items(request, limit: int = 10):
    """Получить топ товаров по рейтингу"""
    items = Item.objects.filter(
        user=request.auth,
        is_active=True
    ).select_related('product').order_by('-elo_rating')[:limit]
    return [serialize_item(item) for item in items]


# ============================================================================
# PARSING ENDPOINTS (Async tasks) - MUST be before /items/{item_id}
# ============================================================================

@router.post("/items/add-from-url", response=TaskResponseSchema, auth=auth)
def add_item_by_url(request, payload: ItemFromUrlSchema):
    """
    Добавить товар по URL (асинхронно)

    Запускает фоновую задачу для парсинга товара.
    Возвращает task_id для отслеживания статуса.
    """
    from .tasks import add_item_from_url

    # Запускаем асинхронную задачу
    task = add_item_from_url.delay(request.auth.id, payload.url)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Товар добавляется в фоновом режиме. Используйте task_id для проверки статуса."
    }


@router.post("/items/add-from-catalog", response=TaskResponseSchema, auth=auth)
def add_items_by_catalog(request, payload: ItemsFromCatalogSchema):
    """
    Добавить товары из каталога (асинхронно)

    Запускает фоновую задачу для парсинга каталога.
    Возвращает task_id для отслеживания статуса.
    """
    from .tasks import add_items_from_catalog

    # Запускаем асинхронную задачу
    task = add_items_from_catalog.delay(
        request.auth.id,
        payload.url,
        payload.max_items
    )

    return {
        "success": True,
        "task_id": task.id,
        "message": f"Парсинг каталога запущен (макс. {payload.max_items} товаров). Используйте task_id для проверки статуса."
    }


@router.post("/items/import-favorites", response=TaskResponseSchema, auth=auth)
def import_favorites(request):
    """
    Импортировать товары из избранного Wildberries

    Запускает фоновую задачу для импорта товаров.
    Пользователю нужно будет авторизоваться в открывшемся браузере.
    """
    from .tasks import import_favorites_from_wildberries

    # Запускаем асинхронную задачу
    task = import_favorites_from_wildberries.delay(request.auth.id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Открылся браузер для авторизации на Wildberries. После входа товары будут автоматически импортированы."
    }


@router.post("/items/import-favorites-bulk", response=TaskResponseSchema, auth=auth)
def import_favorites_bulk(request, payload: WBFavoritesImportSchema):
    """
    Массовый импорт избранного Wildberries из текста (названия + ссылки)

    Принимает сырой текст, где есть WB-ссылки, и запускает фоновую задачу импорта.
    """
    from .tasks import import_favorites_from_text

    if not payload.data or not payload.data.strip():
        raise ValidationError("Передайте список ссылок Wildberries")

    task = import_favorites_from_text.delay(request.auth.id, payload.data)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Массовый импорт избранного запущен в фоновом режиме."
    }


@router.get("/items/{item_id}", response=ItemSchema, auth=auth)
def get_item(request, item_id: int):
    """Получить товар по ID"""
    item = get_object_or_404(
        Item.objects.select_related('product'),
        id=item_id,
        user=request.auth
    )
    return serialize_item(item)


@router.post("/items", response=ItemSchema, auth=auth)
def create_item(request, payload: ItemCreateSchema):
    """Создать новый товар вручную"""
    # UUID гарантирует уникальность без риска IntegrityError от коллизии randint
    article_code = f"MANUAL-{uuid.uuid4().hex[:12].upper()}"

    # Создаем Product
    product = Product.objects.create(
        article_code=article_code,
        name=payload.name,
        marketplace=payload.marketplace,
        url=payload.url,
        price=payload.price,
        image_url=payload.image_url
    )

    # Создаем Item с привязкой к Product
    item = Item.objects.create(
        user=request.auth,
        product=product
    )
    item.refresh_from_db()

    return serialize_item(item)


@router.put("/items/{item_id}", response=ItemSchema, auth=auth)
def update_item(request, item_id: int, payload: ItemCreateSchema):
    """Обновить товар"""
    item = get_object_or_404(Item, id=item_id, user=request.auth)

    # Обновляем Product, если он существует
    if item.product:
        product = item.product
        product.name = payload.name
        product.marketplace = payload.marketplace
        product.url = payload.url
        product.price = payload.price
        product.image_url = payload.image_url
        product.save()
    else:
        # Если Product не существует, создаем его
        article_code = f"MANUAL-{uuid.uuid4().hex[:12].upper()}"
        product = Product.objects.create(
            article_code=article_code,
            name=payload.name,
            marketplace=payload.marketplace,
            url=payload.url,
            price=payload.price,
            image_url=payload.image_url
        )
        item.product = product
        item.save()

    item.refresh_from_db()
    return serialize_item(item)


@router.delete("/items/{item_id}", response=MessageResponseSchema, auth=auth)
def delete_item(request, item_id: int):
    """Удалить товар (soft delete)"""
    item = get_object_or_404(Item, id=item_id, user=request.auth)
    item.is_active = False
    item.save()
    return {"success": True, "message": "Item deleted"}


# ============================================================================
# TASK STATUS ENDPOINT
# ============================================================================

@router.get("/tasks/{task_id}", response=TaskStatusSchema, auth=auth)
def get_task_status(request, task_id: str):
    """
    Получить статус фоновой задачи

    Возвращает статус парсинга товара.
    """
    from celery.result import AsyncResult

    task = AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task.state,  # PENDING, STARTED, SUCCESS, FAILURE
    }

    # Meta/промежуточный результат задачи
    if isinstance(task.info, dict):
        response["result"] = task.info

    if task.state == 'PENDING':
        response["message"] = response.get("result", {}).get("message", "Задача в очереди...")
    elif task.state == 'STARTED':
        response["message"] = response.get("result", {}).get("message", "Задача выполняется...")
    elif task.state == 'SUCCESS':
        result = task.result
        if isinstance(result, dict):
            response["result"] = result
            if result.get('success'):
                response["message"] = result.get('message', 'Задача успешно выполнена')
                response["item"] = result.get('item')
            else:
                response["status"] = 'FAILED'
                response["message"] = result.get('message', 'Ошибка')
        else:
            response["message"] = str(result)
    elif task.state == 'FAILURE':
        response["message"] = f"Ошибка: {str(task.info)}"

    return response


@router.get("/imports/recent", response=List[ImportRunSchema], auth=auth)
def recent_import_runs(request, limit: int = 10):
    """Последние запуски импорта текущего пользователя"""
    safe_limit = max(1, min(limit, 50))

    runs = ImportRun.objects.filter(user=request.auth).order_by('-started_at')[:safe_limit]
    return [
        {
            'id': run.id,
            'source': run.source,
            'status': run.status,
            'started_at': run.started_at.isoformat(),
            'finished_at': run.finished_at.isoformat() if run.finished_at else None,
            'total_links': run.total_links,
            'imported_count': run.imported_count,
            'created_count': run.created_count,
            'reactivated_count': run.reactivated_count,
            'duplicates_count': run.duplicates_count,
            'failed_count': run.failed_count,
            'api_enriched_count': run.api_enriched_count,
            'selenium_enriched_count': run.selenium_enriched_count,
            'fast_import_ms': run.fast_import_ms,
            'enrich_api_ms': run.enrich_api_ms,
            'enrich_selenium_ms': run.enrich_selenium_ms,
            'total_ms': run.total_ms,
            'message': run.message,
        }
        for run in runs
    ]


@router.get("/imports/metrics", response=ImportMetricsSchema, auth=auth)
def import_metrics(request, days: int = 7):
    """Сводные метрики импортов за период"""
    from django.db.models import Avg, Sum

    period_days = max(1, min(days, 90))
    since_dt = timezone.now() - timedelta(days=period_days)

    queryset = ImportRun.objects.filter(user=request.auth, started_at__gte=since_dt)
    runs_count = queryset.count()
    completed_runs = queryset.filter(status='completed').count()

    aggregates = queryset.aggregate(
        total_imported=Sum('imported_count'),
        total_failed=Sum('failed_count'),
        avg_fast_import_ms=Avg('fast_import_ms'),
        avg_total_ms=Avg('total_ms'),
    )

    success_rate_percent = 0.0
    if runs_count > 0:
        success_rate_percent = round((completed_runs / runs_count) * 100, 2)

    return {
        'period_days': period_days,
        'runs_count': runs_count,
        'completed_runs': completed_runs,
        'success_rate_percent': success_rate_percent,
        'total_imported': int(aggregates.get('total_imported') or 0),
        'total_failed': int(aggregates.get('total_failed') or 0),
        'avg_fast_import_ms': int(aggregates['avg_fast_import_ms']) if aggregates.get('avg_fast_import_ms') is not None else None,
        'avg_total_ms': int(aggregates['avg_total_ms']) if aggregates.get('avg_total_ms') is not None else None,
    }


# ============================================================================
# DASHBOARD ENDPOINT
# ============================================================================

@router.get("/dashboard", response=DashboardSchema, auth=auth)
def dashboard(request):
    """Получить статистику для дашборда"""
    from django.db.models import Count, Q

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(days=1)

    # Статистика (оптимизировано: 1 запрос с aggregation)
    stats = Item.objects.filter(user=request.auth).aggregate(
        total_items=Count('id'),
        week_items=Count('id', filter=Q(added_at__gte=week_ago)),
        day_items=Count('id', filter=Q(added_at__gte=day_ago)),
        active_items=Count('id', filter=Q(is_active=True)),
    )

    total_comparisons = Comparison.objects.filter(user=request.auth).count()

    # Топ 3 товара (только с максимальным уровнем уверенности - 5 звезд)
    MIN_COMPARISONS = 20  # Соответствует confidence >= 95% (very_high - максимальный уровень)

    top_items = Item.objects.filter(
        user=request.auth,
        is_active=True,
        comparisons_count__gte=MIN_COMPARISONS
    ).select_related('product').order_by('-elo_rating')[:3]

    # Топ 3 до 1000₽
    top_1000 = Item.objects.filter(
        user=request.auth,
        is_active=True,
        product__price__lte=1000,
        product__price__gt=0,
        comparisons_count__gte=MIN_COMPARISONS
    ).select_related('product').order_by('-elo_rating')[:3]

    # Топ 3 до 10000₽
    top_10000 = Item.objects.filter(
        user=request.auth,
        is_active=True,
        product__price__lte=10000,
        product__price__gt=0,
        comparisons_count__gte=MIN_COMPARISONS
    ).select_related('product').order_by('-elo_rating')[:3]

    return {
        'stats': {
            'total_items': stats['total_items'],
            'week_items': stats['week_items'],
            'day_items': stats['day_items'],
            'active_items': stats['active_items'],
            'total_comparisons': total_comparisons,
        },
        'top_items': [serialize_item(item) for item in top_items],
        'top_1000': [serialize_item(item) for item in top_1000],
        'top_10000': [serialize_item(item) for item in top_10000],
    }


# ============================================================================
# COMPARISON ENDPOINTS
# ============================================================================

@router.get("/compare/pair", response=ComparisonPairSchema, auth=auth)
def get_comparison_pair(request, session_type: str = "all"):
    """Получить пару товаров для сравнения"""
    items = Item.objects.filter(
        user=request.auth,
        is_active=True,
        product__isnull=False,
        product__price__isnull=False,
        product__price__gt=0,
    ).select_related('product').only(
        'id',
        'elo_rating',
        'comparisons_count',
        'wins',
        'losses',
        'product__id',
        'product__name',
        'product__category',
        'product__price',
        'product__marketplace',
        'product__url',
        'product__image_url',
    )

    for marker in INVALID_PRODUCT_NAME_MARKERS:
        items = items.exclude(product__name__icontains=marker)

    if session_type == "top50":
        # Топ 50% по рейтингу
        count = items.count()
        items = items.order_by('-elo_rating')[:count // 2]
    elif session_type == "bottom50":
        # Нижние 50% по рейтингу
        count = items.count()
        items = items.order_by('-elo_rating')[count // 2:]

    item_list = [item for item in items if _is_valid_for_comparison(item)]
    if len(item_list) < 2:
        raise ValidationError(
            "Недостаточно валидных товаров для сравнения. Нужны минимум 2 активных товара с ценой и корректным названием."
        )

    items_by_id = {item.id: item for item in item_list}

    pair = _load_cached_pair(request.auth, session_type, items_by_id)
    if not pair:
        pair = _pick_balanced_pair(item_list)
        if pair:
            _store_cached_pair(request.auth, session_type, pair[0].id, pair[1].id)

    if not pair:
        raise ValidationError("Не удалось подобрать пару для сравнения")

    return {
        "item1": serialize_item(pair[0]),
        "item2": serialize_item(pair[1])
    }


@router.post("/compare", response=ComparisonSchema, auth=auth)
def create_comparison(request, payload: ComparisonCreateSchema):
    """Сохранить результат сравнения"""
    item1 = get_object_or_404(Item, id=payload.item1_id, user=request.auth)
    item2 = get_object_or_404(Item, id=payload.item2_id, user=request.auth)
    winner = get_object_or_404(Item, id=payload.winner_id, user=request.auth)

    # Валидация: winner должен быть одним из сравниваемых товаров
    if winner.id not in [item1.id, item2.id]:
        raise ValidationError("Winner must be one of the compared items")

    # Сохранить текущие рейтинги
    item1_before = item1.elo_rating
    item2_before = item2.elo_rating

    # Обновить ELO рейтинги
    if winner.id == item1.id:
        item1.update_elo(item2, won=True)
        item2.update_elo(item1, won=False)
    else:
        item2.update_elo(item1, won=True)
        item1.update_elo(item2, won=False)

    # Обновить данные после изменения
    item1.refresh_from_db()
    item2.refresh_from_db()

    # Создать запись сравнения
    comparison = Comparison.objects.create(
        user=request.auth,
        item1=item1,
        item2=item2,
        winner=winner,
        item1_rating_before=item1_before,
        item2_rating_before=item2_before,
        item1_rating_after=item1.elo_rating,
        item2_rating_after=item2.elo_rating
    )

    _invalidate_pair_cache(request.auth.id)

    return comparison


@router.get("/comparisons", response=List[ComparisonSchema], auth=auth)
def list_comparisons(request, limit: int = 50):
    """Получить историю сравнений"""
    comparisons = Comparison.objects.filter(
        user=request.auth
    ).order_by('-created_at')[:limit]
    return list(comparisons)


# ============================================================================
# STATISTICS & PRICE HISTORY
# ============================================================================

@router.get("/stats", response=StatisticsSchema, auth=auth)
def get_statistics(request):
    """Получить общую статистику"""
    items = Item.objects.filter(
        user=request.auth,
        is_active=True
    ).select_related('product')
    comparisons = Comparison.objects.filter(user=request.auth)

    top_item_obj = items.order_by('-elo_rating').first()
    top_item = serialize_item(top_item_obj) if top_item_obj else None

    return {
        "total_items": items.count(),
        "total_comparisons": comparisons.count(),
        "avg_rating": int(items.aggregate(avg=models.Avg('elo_rating'))['avg'] or 1500),
        "top_item": top_item
    }


@router.get("/items/{item_id}/price-history", response=List[PriceHistorySchema], auth=auth)
def get_price_history(request, item_id: int):
    """Получить историю цен товара"""
    item = get_object_or_404(
        Item.objects.select_related('product'),
        id=item_id,
        user=request.auth
    )
    history = PriceHistory.objects.filter(
        product=item.product
    ).order_by('-checked_at')[:30]

    return [
        {
            "id": h.id,
            "price": float(h.price),
            "checked_at": h.checked_at.isoformat()
        }
        for h in history
    ]


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================

@router.get("/profile", response=ProfileSchema, auth=auth)
def get_profile(request):
    """Получить данные профиля"""
    from authentication.models import UserProfile

    # Получаем или создаем профиль пользователя
    profile, _ = UserProfile.objects.get_or_create(user=request.auth)

    return {
        "username": request.auth.username,
        "email": request.auth.email or "",
        "first_name": request.auth.first_name or "",
        "last_name": request.auth.last_name or "",
        "phone": profile.phone or ""
    }


@router.put("/profile", response=ProfileSchema, auth=auth)
def update_profile(request, payload: ProfileUpdateSchema):
    """Обновить данные профиля"""
    from authentication.models import UserProfile

    user = request.auth

    # Обновляем данные пользователя
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.email is not None:
        # Проверяем уникальность email среди других пользователей
        if User.objects.filter(email=payload.email).exclude(pk=user.pk).exists():
            raise ValidationError('Данный email уже занят другим пользователем')
        user.email = payload.email
    user.save()

    # Обновляем телефон в профиле
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if payload.phone is not None:
        profile.phone = payload.phone
        profile.save()

    return {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": profile.phone or ""
    }


@router.post("/profile/reset-stats", response=MessageResponseSchema, auth=auth)
def reset_statistics(request):
    """Обнулить статистику (сбросить ELO и сравнения)"""
    with transaction.atomic():
        Item.objects.filter(user=request.auth).update(
            elo_rating=1500,
            wins=0,
            losses=0,
            comparisons_count=0,
        )
        Comparison.objects.filter(user=request.auth).delete()

    return {
        "success": True,
        "message": "Статистика обнулена"
    }


@router.post("/profile/delete-all-items", response=MessageWithCountSchema, auth=auth)
def delete_all_items(request):
    """Удалить все товары"""
    # Помечаем все товары как неактивные
    items = Item.objects.filter(user=request.auth)
    count = items.count()
    items.update(is_active=False)

    return {
        "success": True,
        "message": f"Удалено {count} товаров",
        "count": count
    }
