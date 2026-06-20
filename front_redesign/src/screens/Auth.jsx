// src/screens/Auth.jsx — вход и регистрация. Визуально согласован с онбордингом:
// сплошной фон, крупный заголовок, поля как в AddSheet, кнопка-primary.
import React, { useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Btn } from '../components/ui.jsx';

export function Auth({ t, wide, onLogin, onRegister }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const isRegister = mode === 'register';

  async function submit(e) {
    e?.preventDefault?.();
    if (busy) return;
    setError(null);
    if (!email.trim() || !password) {
      setError('Введите email и пароль');
      return;
    }
    setBusy(true);
    try {
      if (isRegister) await onRegister(email.trim(), password);
      else await onLogin(email.trim(), password);
    } catch (err) {
      setError(
        err?.status === 401 ? 'Неверный email или пароль'
          : isRegister ? 'Не удалось зарегистрироваться. Возможно, email уже занят или пароль слишком простой.'
            : 'Не удалось войти. Проверьте данные и попробуйте снова.'
      );
      setBusy(false);
    }
  }

  const field = (label, type, value, onChange, placeholder, autoFocus) => (
    <label style={{ display: 'block', marginBottom: 12 }}>
      <span style={{ display: 'block', fontFamily: t.mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.ink3, marginBottom: 7 }}>{label}</span>
      <input
        type={type} value={value} autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        style={{ width: '100%', boxSizing: 'border-box', border: 'none', outline: 'none', background: 'transparent',
          fontFamily: t.font, fontSize: 14, color: t.ink, padding: '13px 14px', borderRadius: t.radius,
          boxShadow: `inset 0 0 0 ${t.borderW}px ${t.hair}` }}
      />
    </label>
  );

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: wide ? '8px 0' : '8px 22px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 22 }}>
        <span style={{ fontFamily: t.font, fontWeight: 800, fontSize: 26, letterSpacing: '-0.03em', color: t.ink }}>Выбра</span>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: t.accent }} />
      </div>

      <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 34 : 27, lineHeight: 1.05, letterSpacing: t.tight, color: t.ink }}>
        {isRegister ? 'Создать аккаунт' : 'С возвращением'}
      </div>
      <div style={{ fontFamily: t.font, fontSize: wide ? 14 : 13, color: t.ink2, marginTop: 7, marginBottom: 22 }}>
        {isRegister ? 'Пара секунд — и можно сравнивать желания.' : 'Войдите, чтобы продолжить ранжировать.'}
      </div>

      <form onSubmit={submit} style={{ maxWidth: wide ? 380 : 'none' }}>
        {field('Email', 'email', email, setEmail, 'you@example.com', true)}
        {field('Пароль', 'password', password, setPassword, isRegister ? 'минимум 8 символов' : '••••••••', false)}

        {error && (
          <div style={{ fontFamily: t.font, fontSize: 12.5, color: t.bad, margin: '2px 0 12px', lineHeight: 1.4 }}>{error}</div>
        )}

        <Btn t={t} variant="primary" full onClick={submit} disabled={busy} style={{ marginTop: 6 }}>
          {busy ? 'Минуту…' : (isRegister ? 'Зарегистрироваться' : 'Войти')}
          {!busy && <Icon name="arrow" size={18} color={t.bg} />}
        </Btn>
      </form>

      <div style={{ fontFamily: t.font, fontSize: 13, color: t.ink2, marginTop: 18 }}>
        {isRegister ? 'Уже есть аккаунт? ' : 'Ещё нет аккаунта? '}
        <button
          type="button"
          onClick={() => { setError(null); setMode(isRegister ? 'login' : 'register'); }}
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 0, fontFamily: t.font, fontSize: 13, fontWeight: 600, color: t.accent }}
        >
          {isRegister ? 'Войти' : 'Зарегистрироваться'}
        </button>
      </div>
    </div>
  );
}
