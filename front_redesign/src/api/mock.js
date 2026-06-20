// src/api/mock.js — встроенный офлайн-бэкенд (in-memory + localStorage).
// Реализует тот же интерфейс, что и реальный api/client. Активен, пока
// не задан VITE_API_URL. Удобно демонстрировать без сервера.

import { eloUpdate, pickPair } from '../lib/elo.js';

export const SEED = [
  { id: 'nb',     n: 'Кроссовки NB 530, белые',   p: '8 990 ₽',  s: 'WB',   cat: 'shoes',  elo: 1280, r: 4.8 },
  { id: 'asics',  n: 'Asics GT-2000, синие',       p: '11 400 ₽', s: 'WB',   cat: 'shoes',  elo: 1180, r: 4.6 },
  { id: 'stussy', n: 'Толстовка Stussy basic',     p: '6 400 ₽',  s: 'OZON', cat: 'hoodie', elo: 1240, r: 4.7 },
  { id: 'lamp',   n: 'Лампа IKEA Tertial',         p: '1 290 ₽',  s: 'OZON', cat: 'lamp',   elo: 1200, r: 4.5 },
  { id: 'kettle', n: 'Чайник Xiaomi smart',        p: '3 200 ₽',  s: 'OZON', cat: 'kettle', elo: 1160, r: 4.4 },
  { id: 'book',   n: 'Книга «Дзен и искусство»',   p: '790 ₽',    s: 'WB',   cat: 'book',   elo: 1220, r: 4.9 },
  { id: 'mug',    n: 'Кружка керамика 350 мл',     p: '490 ₽',    s: 'WB',   cat: 'mug',    elo: 1100, r: 4.3 },
  { id: 'case',   n: 'Чехол для iPad minimal',     p: '2 100 ₽',  s: 'OZON', cat: 'tablet', elo: 1080, r: 4.5 },
  { id: 'cand',   n: 'Подсвечник стекло',          p: '620 ₽',    s: 'WB',   cat: 'candle', elo: 1090, r: 4.6 },
  { id: 'socks',  n: 'Носки Nike, 3 пары',         p: '790 ₽',    s: 'WB',   cat: 'socks',  elo: 1050, r: 4.4 },
];

const LS = 'vybra_mock_v1';
const load = () => {
  try { return JSON.parse(localStorage.getItem(LS)); } catch { return null; }
};
const save = (db) => { try { localStorage.setItem(LS, JSON.stringify(db)); } catch {} };

let db = load() || { items: SEED, matches: 0, budget: 15000 };
const persist = () => save(db);
const delay = (ms = 120) => new Promise((r) => setTimeout(r, ms));

export const mockApi = {
  // Аутентификация в офлайн-режиме — всегда «вошли» под демо-пользователем.
  async me() { return { id: 0, email: 'demo@vybra.local', username: 'demo' }; },
  async login() { await delay(60); return { success: true }; },
  async register() { await delay(60); return { success: true }; },
  async logout() { return { success: true }; },

  async getState() {
    await delay();
    return JSON.parse(JSON.stringify(db));
  },
  // Возвращает ту же форму, что бэкенд: дельты применяет useApp.
  async recordMatch(winnerId, loserId) {
    await delay(80);
    const w = db.items.find((x) => x.id === winnerId);
    const l = db.items.find((x) => x.id === loserId);
    if (!w || !l) return { item1_id: winnerId, item2_id: loserId, item1_rating_after: 0, item2_rating_after: 0 };
    const [we, le] = eloUpdate(w, l);
    w.elo = we; l.elo = le; db.matches += 1; persist();
    return { item1_id: winnerId, item2_id: loserId, item1_rating_after: we, item2_rating_after: le };
  },
  async addItem(item) {
    await delay();
    const it = { id: 'u' + Date.now(), n: item.n, p: item.p, s: item.s, cat: item.cat, elo: 1200, r: item.r ?? 4.6 };
    db.items.push(it); persist();
    return it;
  },
  async deleteItem(id) {
    await delay(80);
    db.items = db.items.filter((x) => x.id !== id); persist();
    return { ok: true };
  },
  async setBudget(v) {
    db.budget = v; persist();
    return { budget: v };
  },
  async reset() {
    db = { items: SEED, matches: 0, budget: 15000 }; persist();
    return JSON.parse(JSON.stringify(db));
  },
  async importFavorites() {
    await delay(400);
    return { imported: 0, created: 0, message: 'В демо-режиме импорт недоступен' };
  },
  async priceHistory() {
    await delay(60);
    return [];
  },
  nextPair: () => pickPair(db.items, []),
};

// Фейковый парсер ссылки маркетплейса. В реальном API это эндпоинт
// POST /preview { url } -> { n, p, s, cat } (см. BACKEND.md).
export function parsePreview(url) {
  if (!url || url.length < 5) return null;
  const u = url.toLowerCase();
  const known = [
    { k: 'jordan', n: 'Jordan 1 Mid, чёрно-белые', p: '14 990 ₽', s: 'WB',   cat: 'shoes' },
    { k: 'kindle', n: 'Kindle Paperwhite 11 gen',   p: '12 500 ₽', s: 'OZON', cat: 'book' },
    { k: 'sony',   n: 'Наушники Sony WH-1000XM5',   p: '29 990 ₽', s: 'OZON', cat: 'headphones' },
    { k: 'arket',  n: 'Худи Arket organic cotton',  p: '7 900 ₽',  s: 'WB',   cat: 'hoodie' },
  ];
  const hit = known.find((x) => u.includes(x.k));
  if (hit) return hit;
  const isWB = u.includes('wildberries') || u.includes('wb.');
  const isOZ = u.includes('ozon');
  return {
    n: 'Товар по ссылке',
    p: ((Math.floor(Math.random() * 9) + 2) * 1000).toLocaleString('ru-RU') + ' ₽',
    s: isOZ ? 'OZON' : (isWB ? 'WB' : 'URL'), cat: 'generic',
  };
}

export const SAMPLE_LINKS = [
  { url: 'wildberries.ru/catalog/jordan-1', tag: 'Jordan 1, WB' },
  { url: 'ozon.ru/product/kindle',          tag: 'Kindle, Ozon' },
  { url: 'ozon.ru/product/sony-wh1000',     tag: 'Sony WH-1000, Ozon' },
  { url: 'wildberries.ru/catalog/arket',    tag: 'Худи Arket, WB' },
];
