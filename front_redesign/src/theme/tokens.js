// src/theme/tokens.js
// Финальное направление — «Контраст» (editorial, bold). Светлая + тёмная темы.
// Палитра вынесена сюда; чтобы поменять акцент глобально — правь ACCENT.

export const ACCENT = '#FF4D2E'; // вермилион — выбранный акцент

const PALETTE = {
  light: {
    bg: '#FFFFFF', surface: '#FFFFFF', surface2: '#F4F4F2', ink: '#0A0A0A',
    ink2: 'rgba(10,10,10,0.58)', ink3: 'rgba(10,10,10,0.40)',
    hair: 'rgba(10,10,10,0.14)', hairSoft: 'rgba(10,10,10,0.08)',
    fill: 'rgba(10,10,10,0.05)', fill2: 'rgba(10,10,10,0.08)',
    appBg: '#ECEAE4',
  },
  dark: {
    bg: '#000000', surface: '#0D0D0D', surface2: '#171717', ink: '#FFFFFF',
    ink2: 'rgba(255,255,255,0.60)', ink3: 'rgba(255,255,255,0.40)',
    hair: 'rgba(255,255,255,0.16)', hairSoft: 'rgba(255,255,255,0.09)',
    fill: 'rgba(255,255,255,0.05)', fill2: 'rgba(255,255,255,0.09)',
    appBg: '#0C0C0E',
  },
};

const BASE = {
  accent: ACCENT, good: '#16A34A', bad: '#FF4D2E',
  font: "'Manrope', system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
  radius: 8, radiusSm: 5, radiusLg: 12, borderW: 1.5,
  hWeight: 800, tight: '-0.03em', bigElo: true,
};

export function hexA(hex, a) {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((x) => x + x).join('') : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

// Возвращает плоский объект токенов под текущую тему/акцент.
export function makeTokens(dark = false, accentOverride) {
  const c = dark ? PALETTE.dark : PALETTE.light;
  const accent = accentOverride || BASE.accent;
  return {
    dark, ...c, ...BASE, accent,
    hi: accent,
    accentSoft: dark ? hexA(accent, 0.22) : hexA(accent, 0.12),
    hiSoft: dark ? hexA(accent, 0.22) : hexA(accent, 0.12),
  };
}

// Категории → оттенок плейсхолдера + иконка
export const CAT = {
  shoes:      { h: 30,   label: 'обувь',  icon: 'shoe' },
  hoodie:     { h: 255,  label: 'одежда', icon: 'shirt' },
  lamp:       { h: 82,   label: 'свет',   icon: 'lamp' },
  kettle:     { h: 205,  label: 'кухня',  icon: 'kettle' },
  book:       { h: 150,  label: 'книга',  icon: 'book' },
  mug:        { h: 38,   label: 'посуда', icon: 'mug' },
  tablet:     { h: 285,  label: 'гаджет', icon: 'tablet' },
  candle:     { h: 62,   label: 'декор',  icon: 'candle' },
  socks:      { h: 340,  label: 'одежда', icon: 'socks' },
  headphones: { h: 265,  label: 'аудио',  icon: 'headphones' },
  generic:    { h: null, label: 'товар',  icon: 'box' },
};
export const catTint = (h, dark) =>
  h == null ? (dark ? '#26262a' : '#ECECEA') : `oklch(${dark ? 0.30 : 0.925} ${dark ? 0.055 : 0.05} ${h})`;
export const catStroke = (h, dark) =>
  h == null ? (dark ? 'rgba(255,255,255,.5)' : 'rgba(0,0,0,.42)') : `oklch(${dark ? 0.80 : 0.48} ${dark ? 0.10 : 0.11} ${h})`;

export const fmtRub = (n) => n.toLocaleString('ru-RU') + ' ₽';
export const rubVal = (s) => parseInt(String(s).replace(/\D/g, ''), 10) || 0;
