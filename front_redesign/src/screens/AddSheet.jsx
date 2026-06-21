// src/screens/AddSheet.jsx — добавление товара. Bottom-sheet на мобиле,
// центрированный диалог на десктопе. Два режима:
//   • «По ссылке» — асинхронный парсинг на бэкенде (Celery+Selenium), с прогрессом
//     и аккуратным таймаутом. Требует поднятого parsing-overlay.
//   • «Вручную» — имя/цена/источник, создаётся сразу через каталог. Работает всегда.
import React, { useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Btn, Card, Pill, CatBlock, Stars } from '../components/ui.jsx';
import { previewUrl, SAMPLE_LINKS } from '../api/index.js';

const SOURCES = ['WB', 'OZON', 'URL'];

export function AddSheet({ t, wide, onClose, onAdd, onDone }) {
  const [mode, setMode] = useState('link'); // 'link' | 'manual'
  const [url, setUrl] = useState('');
  const [preview, setPreview] = useState(null);
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [source, setSource] = useState('WB');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function onUrlChange(v) {
    setError(null);
    setUrl(v);
    if (!v || v.length < 5) { setPreview(null); return; }
    setPreview(await previewUrl(v));
  }

  async function submit(payload, okMessage) {
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      await onAdd(payload);
      onDone(okMessage);
    } catch (e) {
      setError(
        e?.status === 504 ? 'Долго не отвечает. Парсинг товара включается отдельным сервисом — попробуйте позже или добавьте вручную.'
          : e?.status === 502 ? 'Не удалось получить данные товара по ссылке. Добавьте вручную.'
            : 'Не удалось добавить товар. Попробуйте ещё раз.'
      );
      setBusy(false);
    }
  }

  const Tabs = (
    <div style={{ display: 'flex', gap: 4, background: t.fill, padding: 3, borderRadius: t.radius, marginBottom: 16 }}>
      {[['link', 'По ссылке'], ['manual', 'Вручную']].map(([id, label]) => (
        <button key={id} onClick={() => { setMode(id); setError(null); }} disabled={busy}
          style={{ flex: 1, border: 'none', cursor: busy ? 'default' : 'pointer', padding: '8px 0', borderRadius: t.radiusSm,
            background: mode === id ? t.surface : 'transparent', color: mode === id ? t.ink : t.ink2,
            fontFamily: t.font, fontWeight: 600, fontSize: 12.5, boxShadow: mode === id ? `0 1px 4px rgba(0,0,0,.08)` : 'none' }}>
          {label}
        </button>
      ))}
    </div>
  );

  const errorBox = error && (
    <div style={{ fontFamily: t.font, fontSize: 12, color: t.bad, marginTop: 12, lineHeight: 1.4 }}>{error}</div>
  );

  const LinkMode = (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderRadius: t.radius, boxShadow: `inset 0 0 0 ${t.borderW}px ${t.hair}` }}>
        <Icon name="link" size={17} color={t.ink3} />
        <input type="text" value={url} onChange={(e) => onUrlChange(e.target.value)} autoFocus placeholder="wildberries.ru/catalog/12345…" disabled={busy}
          style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontFamily: t.mono, fontSize: 12, color: t.ink }} />
        {url && !busy && <span onClick={() => onUrlChange('')} style={{ cursor: 'pointer', color: t.ink3, display: 'flex' }}><Icon name="cross" size={15} color={t.ink3} /></span>}
      </div>
      <div style={{ fontFamily: t.font, fontSize: 10.5, color: t.ink3, marginTop: 7 }}>WB · Ozon · Я.Маркет · Lamoda</div>

      {!url && !busy && (
        <div style={{ marginTop: 18 }}>
          <div style={{ fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 9 }}>Попробуй</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
            {SAMPLE_LINKS.map((l, i) => (
              <button key={i} onClick={() => onUrlChange(l.url)} style={{ border: 'none', cursor: 'pointer', background: t.fill, fontFamily: t.font, fontWeight: 500, fontSize: 11.5, color: t.ink, padding: '7px 11px', borderRadius: 999 }}>{l.tag}</button>
            ))}
          </div>
        </div>
      )}

      {url && preview && (
        <div style={{ marginTop: 18, animation: 'hf-rise .2s ease-out' }}>
          <div style={{ fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 9 }}>Распознали ссылку</div>
          <Card t={t} style={{ padding: 12, display: 'flex', gap: 12 }}>
            <CatBlock cat={preview.cat} t={t} iconSize={28} style={{ width: 64, height: 64, flex: '0 0 auto' }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: t.font, fontSize: 13.5, fontWeight: 600, lineHeight: 1.25, color: t.ink }}>{preview.n}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 6 }}>
                <Pill t={t} tone="line" style={{ fontSize: 8.5, padding: '2px 6px' }}>{preview.s}</Pill>
                <span style={{ fontFamily: t.font, fontSize: 10.5, color: t.ink3 }}>данные подтянем после добавления</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {errorBox}

      <Btn t={t} variant="primary" full disabled={!preview || busy} onClick={() => submit({ ...preview, url }, '+1 товар в избранном')} style={{ marginTop: 18 }}>
        {busy ? 'Получаем данные товара…' : preview ? 'Добавить в избранное' : 'Вставь ссылку на товар'}
      </Btn>
      {busy && (
        <div style={{ fontFamily: t.font, fontSize: 11, color: t.ink3, textAlign: 'center', marginTop: 9, lineHeight: 1.4 }}>
          Парсинг с маркетплейса может занять до минуты
        </div>
      )}
    </>
  );

  const ManualMode = (
    <>
      <label style={{ display: 'block' }}>
        <span style={{ display: 'block', fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 7 }}>Название</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} autoFocus placeholder="Например, Кроссовки NB 530" disabled={busy}
          style={{ width: '100%', boxSizing: 'border-box', border: 'none', outline: 'none', background: 'transparent', fontFamily: t.font, fontSize: 14, color: t.ink, padding: '12px 14px', borderRadius: t.radius, boxShadow: `inset 0 0 0 ${t.borderW}px ${t.hair}` }} />
      </label>

      <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
        <label style={{ flex: 1 }}>
          <span style={{ display: 'block', fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 7 }}>Цена, ₽</span>
          <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="8990" disabled={busy}
            style={{ width: '100%', boxSizing: 'border-box', border: 'none', outline: 'none', background: 'transparent', fontFamily: t.font, fontSize: 14, color: t.ink, padding: '12px 14px', borderRadius: t.radius, boxShadow: `inset 0 0 0 ${t.borderW}px ${t.hair}` }} />
        </label>
        <div style={{ flex: '0 0 auto' }}>
          <span style={{ display: 'block', fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 7 }}>Источник</span>
          <div style={{ display: 'flex', gap: 3, background: t.fill, padding: 3, borderRadius: t.radius }}>
            {SOURCES.map((s) => (
              <button key={s} onClick={() => setSource(s)} disabled={busy}
                style={{ border: 'none', cursor: busy ? 'default' : 'pointer', padding: '9px 11px', borderRadius: t.radiusSm,
                  background: source === s ? t.surface : 'transparent', color: source === s ? t.ink : t.ink2,
                  fontFamily: t.mono, fontWeight: 600, fontSize: 11 }}>{s}</button>
            ))}
          </div>
        </div>
      </div>

      {errorBox}

      <Btn t={t} variant="primary" full disabled={busy || !name.trim()} onClick={() => submit({ n: name.trim(), p: price, s: source }, '+1 товар в избранном')} style={{ marginTop: 18 }}>
        {busy ? 'Сохраняем…' : 'Добавить в избранное'}
      </Btn>
    </>
  );

  const body = (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <button onClick={busy ? undefined : onClose} style={{ border: 'none', background: 'transparent', cursor: busy ? 'default' : 'pointer', fontFamily: t.font, fontSize: 13, color: busy ? t.ink3 : t.ink2 }}>Отмена</button>
        <span style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 15, color: t.ink }}>Добавить товар</span>
        <span style={{ width: 48 }} />
      </div>
      {Tabs}
      {mode === 'link' ? LinkMode : ManualMode}
    </>
  );

  return (
    <>
      <div onClick={busy ? undefined : onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 30, animation: 'hf-fade .18s ease-out' }} />
      {wide ? (
        <div style={{ position: 'fixed', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', zIndex: 31, width: 440, maxWidth: '92vw', maxHeight: 'calc(var(--app-height) - 48px)', overflowY: 'auto', background: t.surface, borderRadius: t.radiusLg, padding: '18px 22px 24px', boxShadow: '0 24px 64px rgba(0,0,0,0.32)', animation: 'hf-pop-in .22s cubic-bezier(.2,.7,.3,1)' }}>
          {body}
        </div>
      ) : (
        <div style={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 31, maxHeight: 'calc(var(--app-height) - 48px)', overflowY: 'auto', background: t.surface, borderRadius: `${t.radiusLg}px ${t.radiusLg}px 0 0`, padding: '10px 20px calc(26px + var(--safe-bottom))', boxShadow: '0 -12px 32px rgba(0,0,0,0.22)', animation: 'hf-up .24s cubic-bezier(.2,.7,.3,1)' }}>
          <div style={{ width: 38, height: 4, borderRadius: 2, background: t.hair, margin: '2px auto 14px' }} />
          {body}
        </div>
      )}
    </>
  );
}
