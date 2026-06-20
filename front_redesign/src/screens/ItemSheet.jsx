// src/screens/ItemSheet.jsx — деталь товара: крупное фото, цена/рейтинг/ELO,
// история цен (спарклайн из /items/{id}/price-history), удаление и ссылка на
// маркетплейс. Bottom-sheet на мобиле, центрированный диалог на десктопе.
import React, { useEffect, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Btn, Thumb, Pill, EloTag, Stars, Spark } from '../components/ui.jsx';
import { api } from '../api/index.js';

export function ItemSheet({ t, wide, item, onClose, onDelete }) {
  const [history, setHistory] = useState(null); // null=loading, []=нет данных

  useEffect(() => {
    let alive = true;
    api.priceHistory(item.id)
      .then((h) => { if (alive) setHistory(Array.isArray(h) ? h : []); })
      .catch(() => { if (alive) setHistory([]); });
    return () => { alive = false; };
  }, [item.id]);

  // Бэкенд отдаёт по убыванию даты — для графика разворачиваем в хронологию.
  const series = history ? history.map((p) => p.price).reverse() : [];

  const body = (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <button onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontFamily: t.font, fontSize: 13, color: t.ink2 }}>Закрыть</button>
        <span style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 15, color: t.ink }}>Товар</span>
        <span style={{ width: 52 }} />
      </div>

      <Thumb img={item.img} cat={item.cat} t={t} iconSize={56} rounded={t.radius} store={item.s} style={{ width: '100%', height: 180 }} />

      <div style={{ marginTop: 14 }}>
        <div style={{ fontFamily: t.font, fontSize: 15, fontWeight: 600, lineHeight: 1.3, color: t.ink }}>{item.n}</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
          <span style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 22, letterSpacing: t.tight, color: t.ink }}>{item.p}</span>
          <EloTag t={t} big>{item.elo}</EloTag>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
          <Pill t={t} tone="line" style={{ fontSize: 9, padding: '2px 7px' }}>{item.s}</Pill>
          <Stars t={t} val={item.r || 4.6} size={12} />
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <div style={{ fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 8 }}>История цены</div>
        {history === null ? (
          <div style={{ fontFamily: t.mono, fontSize: 12, color: t.ink3 }}>загрузка…</div>
        ) : series.length >= 2 ? (
          <Spark t={t} data={series} w={wide ? 380 : 300} h={56} />
        ) : (
          <div style={{ fontFamily: t.font, fontSize: 12, color: t.ink3, lineHeight: 1.4 }}>
            Пока одна точка. График появится после обновлений цены.
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
        <Btn t={t} variant="ghost" onClick={() => { onDelete(item.id); onClose(); }} style={{ flex: '0 0 auto', color: t.bad }}>
          <Icon name="trash" size={16} color={t.bad} /> Удалить
        </Btn>
        {item.url && (
          <Btn t={t} variant="primary" full onClick={() => window.open(item.url, '_blank', 'noopener')}>
            На маркетплейсе <Icon name="arrow" size={16} color={t.bg} />
          </Btn>
        )}
      </div>
    </>
  );

  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 30, animation: 'hf-fade .18s ease-out' }} />
      {wide ? (
        <div style={{ position: 'fixed', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', zIndex: 31, width: 440, maxWidth: '92vw', maxHeight: '90vh', overflowY: 'auto', background: t.surface, borderRadius: t.radiusLg, padding: '18px 22px 24px', boxShadow: '0 24px 64px rgba(0,0,0,0.32)', animation: 'hf-pop-in .22s cubic-bezier(.2,.7,.3,1)' }}>
          {body}
        </div>
      ) : (
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, zIndex: 31, maxHeight: '92%', overflowY: 'auto', background: t.surface, borderRadius: `${t.radiusLg}px ${t.radiusLg}px 0 0`, padding: '10px 20px 26px', boxShadow: '0 -12px 32px rgba(0,0,0,0.22)', animation: 'hf-up .24s cubic-bezier(.2,.7,.3,1)' }}>
          <div style={{ width: 38, height: 4, borderRadius: 2, background: t.hair, margin: '2px auto 14px' }} />
          {body}
        </div>
      )}
    </>
  );
}
