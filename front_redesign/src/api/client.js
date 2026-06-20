// src/api/client.js — реальный HTTP-клиент к Django Ninja API.
// Канонический контракт — существующий бэкенд (/api/auth/*, /api/wishlist/*).
// Вся трансформация форм данных — в transform.js. UI работает только с front-формой.

import { toFrontItem, previewToFront, sourceFromMarketplace, marketplaceFromSource, rubVal } from './transform.js';

const BASE = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function rawFetch(path, options = {}) {
  return fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...options,
  });
}

// Один общий refresh на все параллельные запросы, чтобы не дёргать /refresh N раз.
let refreshing = null;

async function req(path, options = {}, retried = false) {
  const res = await rawFetch(path, options);

  if (res.status === 401 && !retried) {
    if (!refreshing) {
      refreshing = rawFetch('/api/auth/refresh', { method: 'POST', body: '{}' })
        .finally(() => { refreshing = null; });
    }
    const refreshed = await refreshing;
    if (refreshed.ok) return req(path, options, true);
    throw new ApiError(401, 'unauthorized');
  }

  if (!res.ok) throw new ApiError(res.status, `API ${res.status} ${path}`);
  return res.status === 204 ? null : res.json();
}

// ─── Оптимистичное превью ссылки (без сетевого парсинга) ────────────────────
// Надёжный парсинг WB требует Selenium (API закрыт x-pow), поэтому живое превью
// на каждый ввод не делаем. Показываем, что распознали по самой ссылке; реальные
// данные подтянет асинхронное добавление.
function detectMarketplace(url) {
  const u = (url || '').toLowerCase();
  if (u.includes('wildberries') || u.includes('wb.ru')) return 'wildberries';
  if (u.includes('ozon')) return 'ozon';
  return 'other';
}

async function preview(url) {
  if (!url || url.trim().length < 5) return null;
  const marketplace = detectMarketplace(url);
  return previewToFront({ name: 'Товар по ссылке', price: null, marketplace, category: null });
}

// ─── Поллинг асинхронной задачи добавления ──────────────────────────────────
async function pollTask(taskId, { interval = 1500, timeout = 60000 } = {}) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const st = await req(`/api/wishlist/tasks/${taskId}`);
    if (st.status === 'SUCCESS') return st;
    if (st.status === 'FAILURE' || st.status === 'FAILED') {
      throw new ApiError(502, st.message || 'Не удалось добавить товар');
    }
    await new Promise((r) => setTimeout(r, interval));
  }
  throw new ApiError(504, 'Добавление заняло слишком много времени');
}

export const httpApi = {
  // ─── Аутентификация ───────────────────────────────────────────────────────
  me: () => req('/api/auth/me'),
  login: (email, password) =>
    req('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email, password) =>
    req('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  logout: () => req('/api/auth/logout', { method: 'POST', body: '{}' }),

  // ─── Состояние ────────────────────────────────────────────────────────────
  getState: async () => {
    const st = await req('/api/wishlist/state');
    return { items: st.items.map(toFrontItem), matches: st.matches, budget: st.budget };
  },

  // Серверный подбор пары (сбалансирован по категории/цене, с кэшем).
  // <2 валидных товаров → 4xx; возвращаем пустую пару, экран показывает заглушку.
  nextPair: async () => {
    try {
      const p = await req('/api/wishlist/compare/pair');
      return [toFrontItem(p.item1), toFrontItem(p.item2)];
    } catch (e) {
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) return [];
      throw e;
    }
  },

  // ELO считается на сервере; клиент сообщает только победителя.
  recordMatch: (winnerId, loserId) =>
    req('/api/wishlist/compare', {
      method: 'POST',
      body: JSON.stringify({ item1_id: winnerId, item2_id: loserId, winner_id: winnerId }),
    }),

  deleteItem: (id) => req(`/api/wishlist/items/${id}`, { method: 'DELETE' }),

  setBudget: (budget) =>
    req('/api/wishlist/budget', { method: 'PUT', body: JSON.stringify({ budget }) }),

  // reset = сброс рейтинга и истории сравнений (товары сохраняются).
  reset: async () => {
    await req('/api/wishlist/profile/reset-stats', { method: 'POST', body: '{}' });
    const st = await req('/api/wishlist/state');
    return { items: st.items.map(toFrontItem), matches: st.matches, budget: st.budget };
  },

  // Массовый импорт избранного WB из share-текста (браузерное расширение).
  // Асинхронно: быстрый этап создаёт товары, обогащение идёт фоном (Celery).
  importFavorites: async (data) => {
    const { task_id } = await req('/api/wishlist/items/import-favorites-bulk', {
      method: 'POST',
      body: JSON.stringify({ data }),
    });
    const st = await pollTask(task_id, { interval: 1500, timeout: 120000 });
    return st.result || {};
  },

  // История цен товара (для детали в избранном).
  priceHistory: (id) => req(`/api/wishlist/items/${id}/price-history`),

  // ─── Добавление товара ─────────────────────────────────────────────────────
  // По ссылке — асинхронно (Celery + Selenium): запускаем задачу и поллим статус.
  // Вручную (без url) — синхронно через каталог.
  preview,
  addItem: async (payload) => {
    if (payload.url) {
      const { task_id } = await req('/api/wishlist/items/add-from-url', {
        method: 'POST',
        body: JSON.stringify({ url: payload.url }),
      });
      await pollTask(task_id);
      return null; // состояние перечитывается целиком (см. useApp.addItem)
    }
    const created = await req('/api/wishlist/items', {
      method: 'POST',
      body: JSON.stringify({
        name: payload.n,
        price: rubVal(payload.p) || null,
        marketplace: marketplaceFromSource(payload.s),
      }),
    });
    return toFrontItem(created);
  },
};
