// src/screens/Compare.jsx
import React, { useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Thumb, Stars } from '../components/ui.jsx';

export function Compare({ t, pair, matches, wide, onPick }) {
  const [picked, setPicked] = useState(null);
  const [bump, setBump] = useState(null);
  const [a, b] = pair;
  if (!a || !b) return <div style={{ flex: 1 }} />;

  function pick(side) {
    if (picked) return;
    setPicked(side);
    const winner = side === 'A' ? a : b;
    const loser = side === 'A' ? b : a;
    // показываем +ELO мгновенно (ожидаемый прирост), затем фиксируем матч
    const exp = 1 / (1 + Math.pow(10, (loser.elo - winner.elo) / 400));
    setBump(Math.round(24 * (1 - exp)));
    setTimeout(() => {
      onPick(winner, loser);
      setPicked(null); setBump(null);
    }, 420);
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: wide ? '6px 0 14px' : '6px 20px 10px', flex: '0 0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 30 : 20, letterSpacing: t.tight, color: t.ink }}>Что хочется сильнее?</div>
          <div style={{ fontFamily: t.font, fontSize: wide ? 13 : 11.5, color: t.ink2, marginTop: 3 }}>Нажми на одну из карточек</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: t.mono, fontSize: wide ? 20 : 16, color: t.ink, fontVariantNumeric: 'tabular-nums' }}>{matches}</div>
          <div style={{ fontFamily: t.font, fontSize: 9.5, color: t.ink3 }}>матчей</div>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: wide ? 'row' : 'column', gap: wide ? 18 : 10, padding: wide ? '0 0 4px' : '0 16px 12px' }}>
        <Tile t={t} item={a} side="A" picked={picked === 'A'} dim={picked === 'B'} bump={picked === 'A' ? bump : null} onPick={pick} />
        <Tile t={t} item={b} side="B" picked={picked === 'B'} dim={picked === 'A'} bump={picked === 'B' ? bump : null} onPick={pick} />
      </div>
    </div>
  );
}

function Tile({ t, item, side, picked, dim, bump, onPick }) {
  return (
    <div onClick={() => onPick(side)} style={{
      position: 'relative', flex: 1, minHeight: 0, borderRadius: t.radius, overflow: 'hidden', cursor: 'pointer',
      boxShadow: `inset 0 0 0 ${picked ? 2.5 : t.borderW}px ${picked ? t.accent : t.hair}`,
      transform: picked ? 'scale(0.985)' : 'scale(1)', opacity: dim ? 0.5 : 1,
      transition: 'transform .16s, opacity .2s, box-shadow .16s',
    }}>
      <Thumb img={item.img} cat={item.cat} t={t} iconSize={72} rounded={0} style={{ position: 'absolute', inset: 0 }} store={item.s} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 110, background: `linear-gradient(to top, ${t.dark ? 'rgba(10,9,8,0.92)' : 'rgba(255,255,255,0.94)'}, transparent)` }} />
      <div style={{ position: 'absolute', left: 16, right: 16, bottom: 15, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: t.font, fontSize: 15, fontWeight: 600, color: t.ink, lineHeight: 1.25 }}>{item.n}</div>
          <div style={{ fontFamily: t.font, fontSize: 19, fontWeight: t.hWeight, color: t.ink, marginTop: 4, letterSpacing: t.tight }}>{item.p}</div>
        </div>
        <Stars t={t} val={item.r || 4.6} size={13} />
      </div>
      {picked && (
        <div style={{ position: 'absolute', top: 12, right: 12, width: 30, height: 30, borderRadius: '50%', background: t.accent, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="check" size={16} color="#fff" sw={2.4} />
        </div>
      )}
      {bump != null && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', background: t.accent, color: '#fff', fontFamily: t.mono, fontWeight: 600, fontSize: 18, padding: '9px 15px', borderRadius: 999, animation: 'hf-pop .42s cubic-bezier(.2,.7,.3,1) forwards' }}>
          +{bump} ELO
        </div>
      )}
    </div>
  );
}
