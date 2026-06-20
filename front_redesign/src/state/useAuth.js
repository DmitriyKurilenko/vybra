// src/state/useAuth.js — сессия пользователя поверх /api/auth/*.
// status: 'checking' (проверяем cookie) | 'anon' (не вошёл) | 'authed' (вошёл).

import { useState, useEffect, useCallback } from 'react';
import { api, IS_MOCK } from '../api/index.js';

export function useAuth() {
  const [status, setStatus] = useState(IS_MOCK ? 'authed' : 'checking');
  const [user, setUser] = useState(null);

  // Первичная проверка сессии по cookie (GET /api/auth/me).
  useEffect(() => {
    let alive = true;
    api.me()
      .then((u) => { if (alive) { setUser(u); setStatus('authed'); } })
      .catch(() => { if (alive) setStatus('anon'); });
    return () => { alive = false; };
  }, []);

  const login = useCallback(async (email, password) => {
    await api.login(email, password);
    const u = await api.me();
    setUser(u);
    setStatus('authed');
    return u;
  }, []);

  const register = useCallback(async (email, password) => {
    await api.register(email, password);
    const u = await api.me();
    setUser(u);
    setStatus('authed');
    return u;
  }, []);

  const logout = useCallback(async () => {
    try { await api.logout(); } catch { /* всё равно разлогиниваемся локально */ }
    setUser(null);
    setStatus('anon');
  }, []);

  return { status, user, login, register, logout };
}
