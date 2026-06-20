// src/state/useApp.js — состояние приложения поверх api-слоя.
// Грузит состояние только когда пользователь авторизован (enabled), прокидывает
// действия (матч, добавить, удалить, бюджет, сброс). ELO считает сервер.

import { useState, useEffect, useCallback } from 'react';
import { api, IS_MOCK } from '../api/index.js';
import { confidenceFrom } from '../lib/elo.js';

export function useApp(enabled) {
  const [items, setItems] = useState([]);
  const [matches, setMatches] = useState(0);
  const [budget, setBudgetState] = useState(15000);
  const [pair, setPair] = useState([]);
  const [loading, setLoading] = useState(true);

  // Серверный подбор пары (сбалансирован по категории/цене, с кэшем).
  const loadPair = useCallback(async () => {
    const p = await api.nextPair();
    setPair(p || []);
  }, []);

  const reload = useCallback(async () => {
    const st = await api.getState();
    setItems(st.items);
    setMatches(st.matches);
    setBudgetState(st.budget);
    await loadPair();
  }, [loadPair]);

  // Первичная загрузка — после авторизации.
  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    setLoading(true);
    reload().catch(() => {}).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [enabled, reload]);

  const recordMatch = useCallback(async (winner, loser) => {
    const c = await api.recordMatch(winner.id, loser.id);
    // Сервер вернул новые рейтинги обоих товаров — применяем точечно.
    setItems((prev) => prev.map((it) => {
      if (it.id === c.item1_id) return { ...it, elo: c.item1_rating_after };
      if (it.id === c.item2_id) return { ...it, elo: c.item2_rating_after };
      return it;
    }));
    setMatches((m) => m + 1);
    await loadPair();
  }, [loadPair]);

  const addItem = useCallback(async (preview) => {
    const created = await api.addItem(preview);
    // И асинхронное добавление по URL, и ручное создание отражаем целиком.
    await reload();
    return created;
  }, [reload]);

  const deleteItem = useCallback(async (id) => {
    await api.deleteItem(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    await loadPair();
  }, [loadPair]);

  const setBudget = useCallback((v) => {
    const val = Math.max(0, v | 0);
    setBudgetState(val);
    api.setBudget?.(val);
  }, []);

  const reset = useCallback(async () => {
    await api.reset();
    await reload();
  }, [reload]);

  return {
    items, matches, budget, pair, loading, isMock: IS_MOCK,
    confidence: confidenceFrom(matches),
    recordMatch, addItem, deleteItem, setBudget, reset,
  };
}
