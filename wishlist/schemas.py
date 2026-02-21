"""
Pydantic schemas for Django Ninja API
"""
from ninja import Schema
from typing import List, Optional


# Item schemas
class ItemSchema(Schema):
    id: int
    name: str
    article_code: Optional[str] = None
    url: Optional[str] = None
    marketplace: str
    category: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    elo_rating: int
    comparisons_count: int
    wins: int
    losses: int
    confidence: int  # Уверенность в рейтинге (0-100%)
    confidence_level: str  # Текстовое описание: very_low, low, medium, high, very_high


class ItemCreateSchema(Schema):
    name: str
    url: Optional[str] = None
    marketplace: str = "other"
    price: Optional[float] = None
    image_url: Optional[str] = None


class ItemFromUrlSchema(Schema):
    url: str


class ItemsFromCatalogSchema(Schema):
    url: str
    max_items: int = 100


class WBFavoritesImportSchema(Schema):
    data: str


# Dashboard schemas
class DashboardStatsSchema(Schema):
    total_items: int
    week_items: int
    day_items: int
    active_items: int
    total_comparisons: int


class DashboardSchema(Schema):
    stats: DashboardStatsSchema
    top_items: List[ItemSchema]
    top_1000: List[ItemSchema]
    top_10000: List[ItemSchema]


# Task schemas
class TaskResponseSchema(Schema):
    success: bool
    task_id: str
    message: str


class TaskStatusSchema(Schema):
    task_id: str
    status: str  # 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE'
    message: Optional[str] = None
    item: Optional[dict] = None
    result: Optional[dict] = None


class ImportRunSchema(Schema):
    id: int
    source: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    total_links: int
    imported_count: int
    created_count: int
    reactivated_count: int
    duplicates_count: int
    failed_count: int
    api_enriched_count: int
    selenium_enriched_count: int
    fast_import_ms: Optional[int] = None
    enrich_api_ms: Optional[int] = None
    enrich_selenium_ms: Optional[int] = None
    total_ms: Optional[int] = None
    message: Optional[str] = None


class ImportMetricsSchema(Schema):
    period_days: int
    runs_count: int
    completed_runs: int
    success_rate_percent: float
    total_imported: int
    total_failed: int
    avg_fast_import_ms: Optional[int] = None
    avg_total_ms: Optional[int] = None


# Comparison schemas
class ComparisonSchema(Schema):
    id: int
    item1_id: int
    item2_id: int
    winner_id: int
    item1_rating_before: int
    item2_rating_before: int
    item1_rating_after: int
    item2_rating_after: int


class ComparisonCreateSchema(Schema):
    item1_id: int
    item2_id: int
    winner_id: int


class ComparisonPairSchema(Schema):
    item1: ItemSchema
    item2: ItemSchema


# Price history schema
class PriceHistorySchema(Schema):
    id: int
    price: float
    checked_at: str


# Statistics schema
class StatisticsSchema(Schema):
    total_items: int
    total_comparisons: int
    avg_rating: int
    top_item: Optional[ItemSchema] = None


# Profile schemas
class ProfileSchema(Schema):
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class ProfileUpdateSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


# Generic response schemas
class MessageResponseSchema(Schema):
    success: bool
    message: str


class MessageWithCountSchema(Schema):
    success: bool
    message: str
    count: Optional[int] = None


class ErrorSchema(Schema):
    error: str
