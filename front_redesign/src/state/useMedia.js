// src/state/useMedia.js — простой брейкпоинт-хук для адаптивной вёрстки.
import { useState, useEffect } from 'react';

export function useMedia(query = '(min-width: 1000px)') {
  const get = () => (typeof window !== 'undefined' ? window.matchMedia(query).matches : false);
  const [match, setMatch] = useState(get);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setMatch(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return match;
}

// удобные алиасы
export const useDesktop = () => useMedia('(min-width: 1000px)');

// тема в localStorage
export function useTheme() {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('vybra_dark') === '1'; } catch { return false; }
  });
  useEffect(() => {
    try { localStorage.setItem('vybra_dark', dark ? '1' : '0'); } catch {}
  }, [dark]);
  return [dark, setDark];
}
