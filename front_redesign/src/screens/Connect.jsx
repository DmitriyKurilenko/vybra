// src/screens/Connect.jsx — подключение источников (шаг онбординга).
// Wildberries: реальный массовый импорт избранного из share-текста (его готовит
// браузерное расширение Vybra). Импорт асинхронный (Celery) — с прогрессом и
// аккуратным таймаутом. Ozon/«по ссылке» — информационные (добавление в приложении).
import React, { useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Btn, Card } from '../components/ui.jsx';
import { api } from '../api/index.js';

export function Connect({ t, wide, onDone }) {
  const [panel, setPanel] = useState(null); // 'wb' | null
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const imported = result ? (result.imported ?? result.created ?? 0) : 0;

  async function runImport() {
    if (busy || !text.trim()) return;
    setError(null);
    setBusy(true);
    try {
      const r = await api.importFavorites(text.trim());
      setResult(r);
    } catch (e) {
      setError(
        e?.status === 504 ? 'Импорт долго не отвечает. Парсинг включается отдельным сервисом — попробуйте позже.'
          : 'Не удалось импортировать. Проверьте текст из расширения и попробуйте снова.'
      );
    }
    setBusy(false);
  }

  const sources = [
    { id: 'wb', n: 'Wildberries', m: 'импорт всего избранного', glyph: 'WB', actionable: true },
    { id: 'oz', n: 'Ozon', m: 'скоро', glyph: 'OZ', actionable: false },
    { id: 'link', n: 'По ссылке', m: 'добавляйте товары в приложении', glyph: '↗', actionable: false },
  ];

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
      <div style={{ padding: wide ? '6px 0 16px' : '6px 0 12px', flex: '0 0 auto' }}>
        <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 32 : 25, lineHeight: 1.04, letterSpacing: t.tight, color: t.ink }}>Подключи источники</div>
        <div style={{ fontFamily: t.font, fontSize: wide ? 14 : 12, color: t.ink2, marginTop: 6 }}>Импортируй избранное Wildberries или начни с демо.</div>
      </div>

      <div className="hf-scroll" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: wide ? '0 0 8px' : '0 0 8px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: wide ? '1fr 1fr 1fr' : '1fr', gap: 10 }}>
          {sources.map((s) => {
            const open = panel === s.id;
            return (
              <Card key={s.id} t={t} hi={open}
                onClick={s.actionable && !busy ? () => setPanel(open ? null : s.id) : undefined}
                style={{ padding: 14, display: 'flex', alignItems: 'center', gap: 12, cursor: s.actionable ? 'pointer' : 'default', opacity: s.actionable ? 1 : 0.6 }}>
                <div style={{ width: 42, height: 42, borderRadius: t.radiusSm, background: t.fill, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: t.mono, fontSize: 14, fontWeight: 600, color: t.ink }}>{s.glyph}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: t.font, fontWeight: 600, fontSize: 14.5, color: t.ink }}>{s.n}</div>
                  <div style={{ fontFamily: t.font, fontSize: 11.5, color: t.ink2, marginTop: 1 }}>{s.m}</div>
                </div>
                {s.actionable && <Icon name={open ? 'cross' : 'chevR'} size={16} color={t.ink3} />}
              </Card>
            );
          })}
        </div>

        {panel === 'wb' && (
          <div style={{ marginTop: 12, animation: 'hf-rise .2s ease-out' }}>
            {result ? (
              <Card t={t} style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ width: 38, height: 38, borderRadius: '50%', flex: '0 0 auto', background: t.good, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon name="check" size={20} color="#fff" sw={2.2} />
                </span>
                <div>
                  <div style={{ fontFamily: t.font, fontWeight: 700, fontSize: 15, color: t.ink }}>Импортировано {imported} товаров</div>
                  <div style={{ fontFamily: t.font, fontSize: 12, color: t.ink2, marginTop: 2 }}>Цены и фото подтянутся в фоне.</div>
                </div>
              </Card>
            ) : (
              <Card t={t} style={{ padding: 14 }}>
                <div style={{ fontFamily: t.font, fontSize: 12.5, color: t.ink2, lineHeight: 1.45, marginBottom: 10 }}>
                  Открой избранное на Wildberries, нажми <b style={{ color: t.ink }}>«Copy for Vybra»</b> в расширении и вставь сюда.
                </div>
                <textarea
                  value={text} onChange={(e) => setText(e.target.value)} disabled={busy}
                  placeholder="Название товара https://www.wildberries.ru/catalog/12345678/detail.aspx&#10;…"
                  style={{ width: '100%', boxSizing: 'border-box', minHeight: 96, resize: 'vertical', border: 'none', outline: 'none',
                    background: 'transparent', fontFamily: t.mono, fontSize: 11.5, color: t.ink, padding: '12px 14px',
                    borderRadius: t.radius, boxShadow: `inset 0 0 0 ${t.borderW}px ${t.hair}` }}
                />
                {error && <div style={{ fontFamily: t.font, fontSize: 12, color: t.bad, marginTop: 10, lineHeight: 1.4 }}>{error}</div>}
                <Btn t={t} variant="primary" full disabled={busy || !text.trim()} onClick={runImport} style={{ marginTop: 12 }}>
                  {busy ? 'Импортируем…' : 'Импортировать избранное'}
                </Btn>
                {busy && (
                  <div style={{ fontFamily: t.font, fontSize: 11, color: t.ink3, textAlign: 'center', marginTop: 9 }}>
                    Разбор ссылок и парсинг может занять до двух минут
                  </div>
                )}
              </Card>
            )}
          </div>
        )}

        {!panel && (
          <div style={{ fontFamily: t.font, fontSize: 11.5, color: t.ink3, textAlign: 'center', marginTop: 16, lineHeight: 1.5 }}>
            Без импорта стартуем на <span style={{ color: t.ink2 }}>демо-наборе</span>. Нужно ≥ 2 товаров для первых сравнений.
          </div>
        )}
      </div>

      <div style={{ padding: wide ? '12px 0 4px' : '12px 0 22px', flex: '0 0 auto', maxWidth: wide ? 360 : 'none' }}>
        <Btn t={t} variant="primary" full onClick={onDone} disabled={busy}>
          {result ? 'Начать сравнивать' : 'Продолжить'} <Icon name="arrow" size={18} color={t.bg} />
        </Btn>
      </div>
    </div>
  );
}
