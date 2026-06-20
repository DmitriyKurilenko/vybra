// src/screens/Top.jsx
import React from 'react';
import { Icon } from '../components/Icon.jsx';
import { Card, Progress, Thumb, ConfidenceBar, shortName } from '../components/ui.jsx';
import { fmtRub, rubVal } from '../theme/tokens.js';

export function Top({ t, items, matches, confidence, budget, setBudget, wide, onAddMatch }) {
  const sorted = [...items].sort((a, b) => b.elo - a.elo);
  const top3 = sorted.slice(0, 3);
  let left = budget; const fits = [];
  for (const it of sorted) { const v = rubVal(it.p); if (v <= left) { fits.push(it); left -= v; } }
  const fitSum = budget - left;

  const Podium = (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 220 }}>
      <PodiumCol t={t} rank={2} item={top3[1]} blockH={92} barH={36} />
      <PodiumCol t={t} rank={1} item={top3[0]} blockH={124} barH={58} winner />
      <PodiumCol t={t} rank={3} item={top3[2]} blockH={76} barH={22} />
    </div>
  );

  const Budget = (
    <Card t={t} style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon name="wallet" size={18} color={t.ink2} />
          <span style={{ fontFamily: t.font, fontWeight: 600, fontSize: 14.5, color: t.ink }}>Хватает на</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 5, padding: '5px 10px', borderRadius: t.radiusSm, boxShadow: `inset 0 0 0 1px ${t.hair}` }}>
          <input type="number" value={budget} onChange={(e) => setBudget(parseInt(e.target.value || '0', 10))}
            style={{ width: 78, border: 'none', outline: 'none', background: 'transparent', fontFamily: t.font, fontWeight: t.hWeight, fontSize: 16, color: t.ink, textAlign: 'right' }} />
          <span style={{ fontFamily: t.font, fontSize: 12, color: t.ink2 }}>₽</span>
        </div>
      </div>
      <div style={{ marginTop: 12 }}><Progress t={t} value={budget ? Math.min(100, fitSum / budget * 100) : 0} color={t.accent} /></div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7, marginTop: 12 }}>
        {fits.slice(0, wide ? 6 : 4).map((f) => (
          <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 8, borderRadius: t.radiusSm, boxShadow: `inset 0 0 0 1px ${t.hairSoft}` }}>
            <Thumb img={f.img} cat={f.cat} t={t} iconSize={16} style={{ width: 30, height: 30 }} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontFamily: t.font, fontSize: 11, fontWeight: 600, color: t.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{shortName(f.n)}</div>
              <div style={{ fontFamily: t.mono, fontSize: 9.5, color: t.good }}>{f.p}</div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ fontFamily: t.mono, fontSize: 10.5, color: t.ink3, marginTop: 10 }}>итого {fmtRub(fitSum)} · остаётся {fmtRub(left)}</div>
    </Card>
  );

  const List = (
    <div>
      <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 15, letterSpacing: t.tight, color: t.ink, margin: '0 0 6px' }}>Рейтинг целиком</div>
      {sorted.map((x, i) => (
        <div key={x.id} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '9px 0', boxShadow: `inset 0 -1px 0 ${t.hairSoft}` }}>
          <span style={{ fontFamily: t.mono, fontSize: 13, width: 22, color: i < 3 ? t.hi : t.ink3, fontWeight: i < 3 ? 600 : 400 }}>{i + 1}</span>
          <Thumb img={x.img} cat={x.cat} t={t} iconSize={16} style={{ width: 34, height: 34 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: t.font, fontSize: 12.5, fontWeight: 500, color: t.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{x.n}</div>
            <div style={{ fontFamily: t.font, fontSize: 10.5, color: t.ink2 }}>{x.p} · {x.s}</div>
          </div>
          <span style={{ fontFamily: t.mono, fontSize: 15, fontWeight: 600, color: t.ink, fontVariantNumeric: 'tabular-nums' }}>{x.elo}</span>
        </div>
      ))}
    </div>
  );

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: wide ? '6px 0 14px' : '6px 20px 12px', flex: '0 0 auto' }}>
        <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 32 : 25, letterSpacing: t.tight, color: t.ink }}>Топ желаний</div>
        <div style={{ fontFamily: t.font, fontSize: 12, color: t.ink2, marginTop: 5 }}>{items.length} товаров · {matches} сравнений</div>
      </div>
      <div className="hf-scroll" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: wide ? '0 2px 8px' : '0 20px 8px' }}>
        <ConfidenceBar t={t} value={confidence} hint={confidence < 30 ? 'мало данных — сравнивай дальше' : confidence > 70 ? 'топ уже устойчив' : 'продолжай — топ уточняется'} />
        {wide ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 20, alignItems: 'start' }}>
              <div>{Podium}</div>
              <div>{Budget}</div>
            </div>
            <div style={{ marginTop: 22 }}>{List}</div>
          </>
        ) : (
          <>
            <div style={{ marginTop: 20 }}>{Podium}</div>
            <div style={{ marginTop: 18 }}>{Budget}</div>
            <div style={{ marginTop: 20 }}>{List}</div>
          </>
        )}
      </div>
    </div>
  );
}

function PodiumCol({ t, rank, item, blockH, barH, winner }) {
  return (
    <div style={{ flex: 1, textAlign: 'center' }}>
      <div style={{ position: 'relative', marginBottom: 8 }}>
        <Thumb img={item?.img} cat={item?.cat || 'generic'} t={t} iconSize={winner ? 30 : 24} win={winner}
          style={{ height: blockH, boxShadow: winner ? `inset 0 0 0 2px ${t.hi}` : `inset 0 0 0 1px ${t.hair}` }} />
      </div>
      <div style={{ fontFamily: t.font, fontWeight: winner ? t.hWeight : 600, fontSize: 11.5, lineHeight: 1.2, color: t.ink, minHeight: 28 }}>{shortName(item?.n)}</div>
      <div style={{ fontFamily: t.mono, fontSize: 13, color: winner ? t.hi : t.ink3, fontWeight: winner ? 600 : 400, marginTop: 1 }}>{item?.elo || '—'}</div>
      <div style={{ height: barH, marginTop: 7, borderRadius: `${t.radiusSm}px ${t.radiusSm}px 0 0`, background: winner ? t.hi : t.fill2, color: winner ? '#fff' : t.ink2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: t.font, fontWeight: t.hWeight, fontSize: winner ? 20 : 15 }}>{rank}</div>
    </div>
  );
}
