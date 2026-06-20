// src/lib/elo.js — рейтинг как в шахматах.
// ВАЖНО: для продакшена eloUpdate стоит считать НА СЕРВЕРЕ (см. BACKEND.md),
// чтобы рейтинг нельзя было накрутить с клиента. Здесь — для офлайн-мока.

export function eloUpdate(winner, loser, k = 24) {
  const expW = 1 / (1 + Math.pow(10, (loser.elo - winner.elo) / 400));
  return [
    Math.round(winner.elo + k * (1 - expW)),
    Math.round(loser.elo + k * (0 - (1 - expW))),
  ];
}

// Выбираем пару близких по рейтингу товаров (информативнее, чем случайная).
export function pickPair(items, excludeIds = []) {
  let pool = items.filter((x) => !excludeIds.includes(x.id));
  if (pool.length < 2) pool = items;
  if (pool.length < 2) return pool;
  const sorted = [...pool].sort((a, b) => a.elo - b.elo);
  const i = Math.floor(Math.random() * (sorted.length - 1));
  const [a, b] = [sorted[i], sorted[i + 1]];
  return Math.random() < 0.5 ? [a, b] : [b, a];
}

// Грубая оценка «уверенности» топа от числа сыгранных матчей.
export const confidenceFrom = (matches) => Math.min(92, Math.round(matches * 4.3));
