// src/App.jsx — корневой экран.
// Поток: проверка сессии → (онбординг → вход/регистрация) | (подключение → приложение).
import React, { useState } from 'react';
import { makeTokens } from './theme/tokens.js';
import { useApp } from './state/useApp.js';
import { useAuth } from './state/useAuth.js';
import { useDesktop, useTheme } from './state/useMedia.js';
import { Shell } from './components/Shell.jsx';
import { Onboarding } from './screens/Onboarding.jsx';
import { Auth } from './screens/Auth.jsx';
import { Connect } from './screens/Connect.jsx';
import { Compare } from './screens/Compare.jsx';
import { Top } from './screens/Top.jsx';
import { Favorites } from './screens/Favorites.jsx';
import { Profile } from './screens/Profile.jsx';
import { AddSheet } from './screens/AddSheet.jsx';
import { ItemSheet } from './screens/ItemSheet.jsx';

const ONB_KEY = 'vybra_onb_done';     // онбординг просмотрен/пропущен
const FLOW_KEY = 'vybra_flow_done';   // шаг «подключение источников» пройден

const lsGet = (k) => { try { return !!localStorage.getItem(k); } catch { return false; } };
const lsSet = (k) => { try { localStorage.setItem(k, '1'); } catch {} };

export default function App() {
  const wide = useDesktop();
  const [dark, setDark] = useTheme();
  const t = makeTokens(dark);

  const auth = useAuth();
  const app = useApp(auth.status === 'authed');

  const [onbDone, setOnbDone] = useState(() => lsGet(ONB_KEY));
  const [flowDone, setFlowDone] = useState(() => lsGet(FLOW_KEY));
  const [onbStep, setOnbStep] = useState(1);

  const [tab, setTab] = useState('compare');
  const [sheet, setSheet] = useState(false);
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState(null);

  function finishOnb() { lsSet(ONB_KEY); setOnbDone(true); }
  function finishFlow() { lsSet(FLOW_KEY); setFlowDone(true); setTab('compare'); }
  function showToast(m) { setToast(m); setTimeout(() => setToast(null), 2200); }

  async function logout() {
    await auth.logout();
    setTab('compare');
  }

  // Обёртка для экранов вне Shell (онбординг / вход / подключение).
  // height: var(--app-height) + overflow: hidden — фиксит переполнение
  // на iOS, где 100vh включает адресную строку. Safe-area — отступы под
  // статус-бар и home-indicator при viewport-fit=cover.
  const Frame = ({ children }) => (
    <div style={{ height: 'var(--app-height)', background: t.bg, color: t.ink, fontFamily: t.font, display: 'flex', justifyContent: 'center', overflow: 'hidden', paddingTop: 'var(--safe-top)', paddingBottom: 'var(--safe-bottom)', paddingLeft: 'var(--safe-left)', paddingRight: 'var(--safe-right)' }}>
      <div style={{ width: '100%', maxWidth: wide ? 860 : 480, display: 'flex', flexDirection: 'column', padding: wide ? '40px 40px' : '8px 20px', height: '100%', minHeight: 0, overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  );

  const Splash = (
    <div style={{ height: 'var(--app-height)', background: t.bg, color: t.ink3, display: 'grid', placeItems: 'center', fontFamily: t.mono, fontSize: 13 }}>загрузка…</div>
  );

  // — Проверка сессии —
  if (auth.status === 'checking') return Splash;

  // — Не авторизован: онбординг, затем вход/регистрация —
  if (auth.status === 'anon') {
    if (!onbDone) {
      return (
        <Frame>
          <Onboarding
            t={t} wide={wide} step={onbStep}
            onNext={() => (onbStep === 4 ? finishOnb() : setOnbStep(onbStep + 1))}
            onBack={onbStep === 1 ? null : () => setOnbStep(onbStep - 1)}
            onSkip={finishOnb}
          />
        </Frame>
      );
    }
    return (
      <Frame>
        <Auth t={t} wide={wide} onLogin={auth.login} onRegister={auth.register} />
      </Frame>
    );
  }

  // — Авторизован, но не прошёл «подключение источников» —
  if (!flowDone) {
    return (
      <Frame>
        <Connect t={t} wide={wide} onDone={finishFlow} />
      </Frame>
    );
  }

  // — Приложение —
  return (
    <Shell t={t} wide={wide} active={tab} onNav={setTab} dark={dark} setDark={setDark} onReset={app.reset}>
      {app.loading ? (
        <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: t.ink3, fontFamily: t.mono, fontSize: 13 }}>загрузка…</div>
      ) : (
        <>
          {tab === 'compare' && <Compare t={t} wide={wide} pair={app.pair} matches={app.matches} onPick={app.recordMatch} />}
          {tab === 'top' && <Top t={t} wide={wide} items={app.items} matches={app.matches} confidence={app.confidence} budget={app.budget} setBudget={app.setBudget} />}
          {tab === 'list' && <Favorites t={t} wide={wide} items={app.items} confidence={app.confidence} onDelete={app.deleteItem} onAdd={() => setSheet(true)} onOpen={setDetail} />}
          {tab === 'profile' && <Profile t={t} wide={wide} items={app.items} matches={app.matches} confidence={app.confidence} budget={app.budget} dark={dark} setDark={setDark} user={auth.user} onLogout={logout} />}
        </>
      )}
      {sheet && <AddSheet t={t} wide={wide} onClose={() => setSheet(false)} onAdd={app.addItem} onDone={(msg) => { setSheet(false); showToast(msg); }} />}
      {detail && <ItemSheet t={t} wide={wide} item={detail} onClose={() => setDetail(null)} onDelete={app.deleteItem} />}
      {toast && (
        <div style={{ position: 'fixed', left: '50%', bottom: 34, transform: 'translateX(-50%)', zIndex: 2000, background: t.ink, color: t.bg, padding: '11px 18px', borderRadius: 999, fontFamily: t.font, fontSize: 13, fontWeight: 600, boxShadow: '0 8px 26px rgba(0,0,0,.25)', animation: 'hf-toast .25s ease-out' }}>{toast}</div>
      )}
    </Shell>
  );
}
