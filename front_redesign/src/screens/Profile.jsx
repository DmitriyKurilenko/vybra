// src/screens/Profile.jsx
import React from 'react';
import { Icon } from '../components/Icon.jsx';
import { Card, Thumb, ConfidenceBar } from '../components/ui.jsx';
import { fmtRub } from '../theme/tokens.js';

export function Profile({ t, items, matches, confidence, budget, dark, setDark, wide, user, onLogout }) {
  const leader = [...items].sort((a, b) => b.elo - a.elo)[0];
  const displayName = user?.username || user?.email || 'Гость';
  const initial = (displayName.trim()[0] || '?').toUpperCase();
  const Row = ({ label, value, onClick }) => (
    <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 0', boxShadow: `inset 0 -1px 0 ${t.hairSoft}`, cursor: onClick ? 'pointer' : 'default' }}>
      <span style={{ fontFamily: t.font, fontSize: 13.5, color: t.ink }}>{label}</span>
      <span style={{ fontFamily: t.font, fontSize: 13.5, fontWeight: 600, color: t.ink2, display: 'flex', alignItems: 'center', gap: 8 }}>{value}</span>
    </div>
  );

  const Identity = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
      <div style={{ width: 54, height: 54, borderRadius: '50%', background: t.fill, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: t.font, fontWeight: t.hWeight, fontSize: 22, color: t.ink }}>{initial}</div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 18, letterSpacing: t.tight, color: t.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{displayName}</div>
        <div style={{ fontFamily: t.font, fontSize: 12, color: t.ink2, marginTop: 2 }}>{items.length} товаров · {matches} матчей</div>
      </div>
    </div>
  );

  const Stats = (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
      <Card t={t} style={{ padding: 14 }}>
        <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 24, color: t.ink, letterSpacing: t.tight }}>{matches}</div>
        <div style={{ fontFamily: t.font, fontSize: 11, color: t.ink2, marginTop: 2 }}>сравнений</div>
      </Card>
      <Card t={t} style={{ padding: 14 }}>
        <div style={{ fontFamily: t.mono, fontWeight: 700, fontSize: 24, color: t.hi, letterSpacing: t.tight }}>{leader?.elo || '—'}</div>
        <div style={{ fontFamily: t.font, fontSize: 11, color: t.ink2, marginTop: 2 }}>ELO лидера</div>
      </Card>
    </div>
  );

  const Leader = leader ? (
    <Card t={t} hi style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
      <Thumb img={leader.img} cat={leader.cat} t={t} iconSize={22} style={{ width: 44, height: 44 }} win />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: t.mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.hi }}>главное желание</div>
        <div style={{ fontFamily: t.font, fontWeight: 600, fontSize: 13, color: t.ink, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{leader.n}</div>
      </div>
      <span style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 14, color: t.ink }}>{leader.p}</span>
    </Card>
  ) : null;

  const Settings = (
    <div>
      <div style={{ fontFamily: t.mono, fontSize: 10.5, letterSpacing: '0.1em', textTransform: 'uppercase', color: t.ink3, margin: '0 0 4px' }}>Настройки</div>
      <Row label="Бюджет" value={fmtRub(budget)} />
      <Row label="Тёмная тема" value={<>{dark ? 'вкл' : 'выкл'} <Icon name={dark ? 'moon' : 'sun'} size={16} color={t.ink2} /></>} onClick={() => setDark(!dark)} />
      <Row label="Источники" value={<>WB · Ozon <Icon name="chevR" size={15} color={t.ink3} /></>} />
      <Row label="О методе ELO" value={<Icon name="chevR" size={15} color={t.ink3} />} />
      {onLogout && <Row label="Выйти" value={<Icon name="arrow" size={15} color={t.ink3} />} onClick={onLogout} />}
    </div>
  );

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: wide ? '6px 0 14px' : '6px 20px 12px', flex: '0 0 auto' }}>
        <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 32 : 25, letterSpacing: t.tight, color: t.ink }}>Профиль</div>
      </div>
      <div className="hf-scroll" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: wide ? '0 2px 8px' : '0 20px 8px' }}>
        {wide ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28, alignItems: 'start' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>{Identity}<ConfidenceBar t={t} value={confidence} hint="больше матчей — точнее топ" />{Stats}{Leader}</div>
            <div>{Settings}</div>
          </div>
        ) : (
          <>
            {Identity}
            <div style={{ marginTop: 18 }}><ConfidenceBar t={t} value={confidence} hint="больше матчей — точнее топ" /></div>
            <div style={{ marginTop: 16 }}>{Stats}</div>
            <div style={{ marginTop: 8 }}>{Leader}</div>
            <div style={{ marginTop: 22 }}>{Settings}</div>
          </>
        )}
      </div>
    </div>
  );
}
