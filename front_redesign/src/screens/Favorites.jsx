// src/screens/Favorites.jsx
import React, { useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Card, Pill, EloTag, Thumb, ConfidenceBar, Stars } from '../components/ui.jsx';

export function Favorites({ t, items, confidence, wide, onDelete, onAdd, onOpen }) {
  const [open, setOpen] = useState(null);
  const sorted = [...items].sort((a, b) => b.elo - a.elo);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', minHeight: 0 }}>
      <div style={{ padding: wide ? '6px 0 10px' : '6px 20px 8px', flex: '0 0 auto', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 32 : 25, letterSpacing: t.tight, color: t.ink }}>Избранное</div>
          <div style={{ fontFamily: t.font, fontSize: 12, color: t.ink2, marginTop: 5 }}>{items.length} товаров</div>
        </div>
        {wide && (
          <button onClick={onAdd} style={{ display: 'flex', alignItems: 'center', gap: 7, border: 'none', cursor: 'pointer', background: t.ink, color: t.bg, fontFamily: t.font, fontWeight: 600, fontSize: 13, padding: '10px 15px', borderRadius: t.radius }}>
            <Icon name="plus" size={16} color={t.bg} sw={2} /> Добавить
          </button>
        )}
      </div>
      <div style={{ padding: wide ? '0 0 10px' : '0 20px 8px', flex: '0 0 auto', maxWidth: wide ? 420 : 'none' }}>
        <ConfidenceBar t={t} value={confidence} hint={wide ? 'наведи на карточку, чтобы удалить' : 'свайп влево по карточке — удалить'} />
      </div>

      <div className="hf-scroll" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: wide ? '6px 2px 8px' : '4px 20px 90px' }}>
        {wide ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {sorted.map((x) => (
              <Card key={x.id} t={t} onClick={() => onOpen(x)} style={{ overflow: 'hidden', position: 'relative', cursor: 'pointer' }}>
                <div style={{ position: 'relative' }}>
                  <Thumb img={x.img} cat={x.cat} t={t} iconSize={40} rounded={0} style={{ height: 120 }} store={x.s} />
                  <button onClick={(e) => { e.stopPropagation(); onDelete(x.id); }} title="Удалить" style={{ position: 'absolute', top: 8, right: 8, width: 30, height: 30, borderRadius: '50%', border: 'none', cursor: 'pointer', background: t.dark ? 'rgba(0,0,0,.5)' : 'rgba(255,255,255,.75)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon name="trash" size={15} color={t.bad} />
                  </button>
                </div>
                <div style={{ padding: 12 }}>
                  <div style={{ fontFamily: t.font, fontSize: 13, fontWeight: 500, color: t.ink, lineHeight: 1.3, minHeight: 34 }}>{x.n}</div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
                    <span style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 15, color: t.ink, letterSpacing: t.tight }}>{x.p}</span>
                    <EloTag t={t}>{x.elo}</EloTag>
                  </div>
                  <div style={{ marginTop: 8 }}><Stars t={t} val={x.r || 4.6} size={11} /></div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          sorted.map((x) => (
            <div key={x.id} style={{ position: 'relative', overflow: 'hidden', borderRadius: t.radiusSm, boxShadow: `inset 0 -1px 0 ${t.hairSoft}`, marginBottom: 2 }}>
              {open === x.id && (
                <button onClick={() => onDelete(x.id)} style={{ position: 'absolute', top: 0, bottom: 0, right: 0, width: 84, background: t.bad, color: '#fff', border: 'none', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3, fontFamily: t.font, fontSize: 11, fontWeight: 600 }}>
                  <Icon name="trash" size={16} color="#fff" /> удалить
                </button>
              )}
              <div onClick={() => setOpen(open === x.id ? null : x.id)} style={{ transform: open === x.id ? 'translateX(-84px)' : 'none', transition: 'transform .18s cubic-bezier(.2,.7,.3,1)', position: 'relative', zIndex: 1, background: t.bg, display: 'flex', alignItems: 'center', gap: 12, padding: '10px 2px', cursor: 'pointer' }}>
                <span onClick={(e) => { e.stopPropagation(); onOpen(x); }} style={{ flex: '0 0 auto', display: 'flex' }}>
                  <Thumb img={x.img} cat={x.cat} t={t} iconSize={20} style={{ width: 46, height: 46 }} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: t.font, fontSize: 13, fontWeight: 500, color: t.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{x.n}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 3 }}>
                    <span style={{ fontFamily: t.font, fontSize: 11, color: t.ink2 }}>{x.p}</span>
                    <Pill t={t} tone="line" style={{ fontSize: 8.5, padding: '2px 6px' }}>{x.s}</Pill>
                  </div>
                </div>
                <EloTag t={t}>{x.elo}</EloTag>
              </div>
            </div>
          ))
        )}
        {items.length === 0 && (
          <div style={{ textAlign: 'center', padding: '52px 0', fontFamily: t.font, color: t.ink2, fontSize: 13 }}>
            Список пуст.<br />Добавь товары кнопкой ниже.
          </div>
        )}
      </div>

      {!wide && (
        <button onClick={onAdd} aria-label="Добавить" style={{ position: 'absolute', right: 18, bottom: 18, width: 52, height: 52, borderRadius: '50%', background: t.ink, color: t.bg, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 22px -6px rgba(0,0,0,0.4)' }}>
          <Icon name="plus" size={22} color={t.bg} sw={2} />
        </button>
      )}
    </div>
  );
}
