// src/components/ui.jsx — переиспользуемые примитивы (карточки, кнопки, графики).
import React, { useState } from 'react';
import { Icon } from './Icon.jsx';
import { CAT, catTint, catStroke, hexA } from '../theme/tokens.js';

// Бейджи-оверлеи (источник / победитель / категория) — общие для плейсхолдера
// и реального фото.
function Badges({ t, store, win, label, labelText, stroke }) {
  return (
    <>
      {store ? (
        <span style={{ position: 'absolute', top: 8, left: 8, fontFamily: t.mono, fontSize: 9,
          letterSpacing: '0.04em', color: t.dark ? 'rgba(255,255,255,.82)' : 'rgba(0,0,0,.62)',
          background: t.dark ? 'rgba(0,0,0,.30)' : 'rgba(255,255,255,.62)', backdropFilter: 'blur(4px)',
          padding: '2px 6px', borderRadius: 6, textTransform: 'uppercase' }}>{store}</span>
      ) : null}
      {win ? (
        <span style={{ position: 'absolute', top: 8, right: 8, width: 22, height: 22, borderRadius: '50%',
          background: t.hi, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="star" size={12} color="#fff" sw={1.4} />
        </span>
      ) : null}
      {label ? (
        <span style={{ position: 'absolute', bottom: 8, left: 9, fontFamily: t.mono, fontSize: 8.5,
          letterSpacing: '0.08em', textTransform: 'uppercase', color: stroke || (t.dark ? 'rgba(255,255,255,.7)' : 'rgba(0,0,0,.5)'), opacity: 0.85 }}>{labelText}</span>
      ) : null}
    </>
  );
}

export function CatBlock({ cat, t, style, iconSize = 40, store, win, label, rounded }) {
  const m = CAT[cat] || CAT.generic;
  const tint = catTint(m.h, t.dark);
  const stroke = catStroke(m.h, t.dark);
  return (
    <div style={{
      position: 'relative', background: tint, overflow: 'hidden',
      borderRadius: rounded == null ? t.radiusSm : rounded,
      display: 'flex', alignItems: 'center', justifyContent: 'center', ...style,
    }}>
      <Icon name={m.icon} size={iconSize} color={stroke} sw={1.5} />
      <Badges t={t} store={store} win={win} label={label} labelText={m.label} stroke={stroke} />
    </div>
  );
}

// Превью товара: реальное фото (image_url) с фолбэком на CatBlock-плейсхолдер
// при отсутствии или ошибке загрузки. Бейджи одинаковы в обоих случаях.
export function Thumb({ img, cat, t, style, iconSize, store, win, label, rounded }) {
  const [failed, setFailed] = useState(false);
  if (!img || failed) {
    return <CatBlock cat={cat} t={t} style={style} iconSize={iconSize} store={store} win={win} label={label} rounded={rounded} />;
  }
  return (
    <div style={{
      position: 'relative', overflow: 'hidden',
      borderRadius: rounded == null ? t.radiusSm : rounded,
      background: t.dark ? '#1a1a1d' : '#f0efec', ...style,
    }}>
      <img src={img} alt="" loading="lazy" onError={() => setFailed(true)}
        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
      <Badges t={t} store={store} win={win} label={label} labelText={(CAT[cat] || CAT.generic).label} />
    </div>
  );
}

export function Btn({ t, variant = 'primary', children, onClick, style, full, disabled }) {
  const base = {
    fontFamily: t.font, fontWeight: 600, fontSize: 14, cursor: disabled ? 'not-allowed' : 'pointer',
    borderRadius: t.radius, padding: '13px 18px', textAlign: 'center', border: 'none',
    transition: 'transform .12s, opacity .12s', letterSpacing: '0.005em',
    width: full ? '100%' : undefined, opacity: disabled ? 0.4 : 1, lineHeight: 1,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
  };
  const v = {
    primary: { background: t.ink, color: t.bg },
    accent:  { background: t.accent, color: '#fff' },
    outline: { background: 'transparent', color: t.ink, boxShadow: `inset 0 0 0 ${t.borderW}px ${t.hair}` },
    ghost:   { background: t.fill, color: t.ink2 },
    soft:    { background: t.fill, color: t.ink },
  }[variant];
  return <button onClick={disabled ? undefined : onClick} style={{ ...base, ...v, ...style }}>{children}</button>;
}

export function Card({ t, children, style, soft, hi, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: soft ? t.surface2 : t.surface, borderRadius: t.radius,
      boxShadow: `inset 0 0 0 ${hi ? (t.borderW + 0.6) : t.borderW}px ${hi ? t.hi : t.hair}`,
      ...style,
    }}>{children}</div>
  );
}

export function Pill({ t, children, style, tone }) {
  const tones = {
    default: { bg: t.fill, c: t.ink2 },
    ink: { bg: t.ink, c: t.bg },
    accent: { bg: t.accent, c: '#fff' },
    good: { bg: t.dark ? hexA(t.good, .22) : hexA(t.good, .14), c: t.good },
    line: { bg: 'transparent', c: t.ink2, ring: true },
  };
  const x = tones[tone || 'default'];
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: t.font,
      fontWeight: 600, fontSize: 10.5, letterSpacing: '0.01em', padding: '4px 9px', borderRadius: 999,
      background: x.bg, color: x.c, boxShadow: x.ring ? `inset 0 0 0 1px ${t.hair}` : 'none', ...style }}>{children}</span>
  );
}

export function Progress({ t, value, color }) {
  return (
    <div style={{ height: 6, background: t.fill, borderRadius: 999, overflow: 'hidden' }}>
      <div style={{ height: '100%', width: Math.max(0, Math.min(100, value)) + '%', borderRadius: 999,
        background: color || t.hi, transition: 'width .5s cubic-bezier(.2,.7,.3,1)' }} />
    </div>
  );
}

export function EloTag({ t, children, big }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: t.mono,
      fontWeight: 500, fontSize: big ? 13 : 11, color: t.ink, fontVariantNumeric: 'tabular-nums' }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: t.hi }} />{children}
    </span>
  );
}

export function Stars({ t, n = 5, val = 4.7, size = 11 }) {
  return (
    <span style={{ display: 'inline-flex', gap: 1.5, color: t.ink3 }}>
      {Array.from({ length: n }).map((_, i) => (
        <Icon key={i} name="star" size={size} sw={1.2} color={i < Math.round(val) ? t.hi : t.hair} />
      ))}
    </span>
  );
}

export function Spark({ t, data, w = 220, h = 52, color }) {
  const min = Math.min(...data), max = Math.max(...data);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / ((max - min) || 1)) * (h - 6) - 3;
    return [x, y];
  });
  const line = pts.map((pp, i) => (i ? 'L' : 'M') + pp[0].toFixed(1) + ',' + pp[1].toFixed(1)).join(' ');
  const cc = color || t.hi;
  const gid = 'sg' + (t.dark ? 'd' : 'l');
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={cc} stopOpacity="0.18" /><stop offset="1" stopColor={cc} stopOpacity="0" />
      </linearGradient></defs>
      <path d={line + ` L${w},${h} L0,${h} Z`} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={cc} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {pts.slice(-1).map((pp, i) => (<circle key={i} cx={pp[0]} cy={pp[1]} r="3" fill={cc} />))}
    </svg>
  );
}

export function ConfidenceBar({ t, value, hint }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <span style={{ fontFamily: t.font, fontSize: 11.5, fontWeight: 500, color: t.ink2 }}>Уверенность в топе</span>
        <span style={{ fontFamily: t.mono, fontSize: 12, color: t.ink, fontVariantNumeric: 'tabular-nums' }}>{value}%</span>
      </div>
      <Progress t={t} value={value} />
      {hint ? <div style={{ fontFamily: t.font, fontSize: 10.5, color: t.ink3, marginTop: 6 }}>{hint}</div> : null}
    </div>
  );
}

export const shortName = (n) =>
  !n ? '—' : n.split(',')[0].replace(/^(Кроссовки|Толстовка|Книга|Наушники|Худи)\s/, '');
