// src/api/transform.js — трансформация между моделью бэкенда (Django Ninja
// ItemSchema) и компактной формой, которую рендерит UI: {id,n,p,s,cat,elo,r,img}.
// Единственное место маппинга — экраны и состояние работают только с front-формой.

import { fmtRub, rubVal } from '../theme/tokens.js';

// marketplace (бэкенд) → source-бейдж (UI)
export function sourceFromMarketplace(marketplace) {
  switch ((marketplace || '').toLowerCase()) {
    case 'wildberries': return 'WB';
    case 'ozon': return 'OZON';
    default: return 'URL';
  }
}

// source-бейдж (UI) → marketplace (бэкенд) — для ручного создания товара
export function marketplaceFromSource(source) {
  switch ((source || '').toUpperCase()) {
    case 'WB': return 'wildberries';
    case 'OZON': return 'ozon';
    default: return 'other';
  }
}

// Свободная категория бэкенда (или название) → enum плейсхолдеров CAT (tokens.js).
// Бэкенд отдаёт произвольный текст (часто null), поэтому это best-effort по
// ключевым словам с безопасным фолбэком 'generic'.
const CAT_KEYWORDS = [
  ['shoes', ['обув', 'кроссов', 'ботин', 'кед', 'sneaker', 'shoe']],
  ['hoodie', ['худи', 'толстов', 'свитш', 'hoodie', 'кофт', 'джемпер', 'свитер']],
  ['socks', ['носк', 'sock']],
  ['lamp', ['лампа', 'светильник', 'lamp', 'свет']],
  ['kettle', ['чайник', 'kettle']],
  ['book', ['книга', 'книги', 'book', 'kindle']],
  ['mug', ['кружка', 'чашка', 'mug', 'стакан']],
  ['tablet', ['планшет', 'ipad', 'tablet', 'чехол']],
  ['candle', ['свеч', 'подсвечник', 'candle', 'аромат']],
  ['headphones', ['наушник', 'headphone', 'earbud', 'аудио']],
];

export function catFromBackend(category, name) {
  const hay = `${category || ''} ${name || ''}`.toLowerCase();
  for (const [cat, words] of CAT_KEYWORDS) {
    if (words.some((w) => hay.includes(w))) return cat;
  }
  return 'generic';
}

// Backend ItemSchema → front-форма
export function toFrontItem(it) {
  const price = it.price != null ? Math.round(it.price) : null;
  return {
    id: it.id,
    n: it.name || 'Без названия',
    p: price != null ? fmtRub(price) : '—',
    priceVal: price ?? 0,
    s: sourceFromMarketplace(it.marketplace),
    cat: catFromBackend(it.category, it.name),
    elo: it.elo_rating,
    r: it.rating != null ? it.rating : null,
    img: it.image_url || null,
    url: it.url || null,
  };
}

// Превью карточки (для AddSheet) — та же front-форма без id.
export function previewToFront(p) {
  return {
    n: p.name || 'Товар по ссылке',
    p: p.price != null ? fmtRub(Math.round(p.price)) : '',
    s: sourceFromMarketplace(p.marketplace),
    cat: catFromBackend(p.category, p.name),
  };
}

export { rubVal };
