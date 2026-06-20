// src/components/Shell.jsx — адаптивный каркас.
// Десктоп (≥1000px): левый сайдбар + широкая контент-область.
// Мобайл: контент во весь экран + нижняя таб-панель.
import React from 'react';
import { Icon } from './Icon.jsx';

const NAV = [
  { id: 'compare', label: 'Сравнить', icon: 'cards' },
  { id: 'top', label: 'Топ', icon: 'trophy' },
  { id: 'list', label: 'Избранное', icon: 'heart' },
  { id: 'profile', label: 'Профиль', icon: 'user' },
];

export function Shell({ t, wide, active, onNav, dark, setDark, onReset, children }) {
  if (wide) {
    return (
      <div style={{ minHeight: '100vh', background: t.appBg, display: 'flex' }}>
        <aside style={{ width: 244, flex: '0 0 auto', background: t.surface, boxShadow: `inset -1px 0 0 ${t.hair}`, display: 'flex', flexDirection: 'column', padding: '26px 18px', position: 'sticky', top: 0, height: '100vh' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, padding: '0 8px 26px' }}>
            <span style={{ fontFamily: t.font, fontWeight: 800, fontSize: 24, letterSpacing: '-0.03em', color: t.ink }}>Выбра</span>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: t.accent }} />
          </div>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {NAV.map((x) => {
              const on = x.id === active;
              return (
                <button key={x.id} onClick={() => onNav(x.id)} style={{ display: 'flex', alignItems: 'center', gap: 12, border: 'none', cursor: 'pointer', textAlign: 'left', padding: '11px 12px', borderRadius: t.radius, background: on ? t.fill : 'transparent', color: on ? t.ink : t.ink2, fontFamily: t.font, fontWeight: on ? 700 : 500, fontSize: 14.5 }}>
                  <Icon name={x.icon} size={20} sw={on ? 1.9 : 1.6} color={on ? t.ink : t.ink2} />{x.label}
                </button>
              );
            })}
          </nav>
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button onClick={() => setDark(!dark)} style={navBtn(t)}>
              <Icon name={dark ? 'moon' : 'sun'} size={19} color={t.ink2} />{dark ? 'Тёмная тема' : 'Светлая тема'}
            </button>
            <button onClick={onReset} style={navBtn(t)}>
              <Icon name="reset" size={18} color={t.ink2} />Сбросить демо
            </button>
          </div>
        </aside>
        <main style={{ flex: 1, minWidth: 0, display: 'flex', justifyContent: 'center', padding: '34px 40px 48px' }}>
          <div style={{ width: '100%', maxWidth: 860, display: 'flex', flexDirection: 'column', color: t.ink, fontFamily: t.font }}>
            {children}
          </div>
        </main>
      </div>
    );
  }

  // Мобайл
  return (
    <div style={{ minHeight: '100vh', background: t.bg, color: t.ink, fontFamily: t.font, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', position: 'relative', maxWidth: 480, width: '100%', margin: '0 auto' }}>
        {children}
        <div style={{ flex: '0 0 auto', display: 'flex', padding: '8px 8px calc(14px + env(safe-area-inset-bottom))', background: t.surface, boxShadow: `inset 0 1px 0 ${t.hairSoft}`, position: 'sticky', bottom: 0, zIndex: 6 }}>
          {NAV.map((x) => {
            const on = x.id === active;
            return (
              <button key={x.id} onClick={() => onNav(x.id)} style={{ flex: 1, border: 'none', background: 'transparent', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5, padding: '6px 0', color: on ? t.ink : t.ink3 }}>
                <Icon name={x.icon} size={22} sw={on ? 1.9 : 1.6} color={on ? t.ink : t.ink3} />
                <span style={{ fontFamily: t.font, fontSize: 9.5, fontWeight: on ? 600 : 500 }}>{x.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const navBtn = (t) => ({ display: 'flex', alignItems: 'center', gap: 12, border: 'none', cursor: 'pointer', textAlign: 'left', padding: '11px 12px', borderRadius: t.radius, background: 'transparent', color: t.ink2, fontFamily: t.font, fontWeight: 500, fontSize: 13.5 });
