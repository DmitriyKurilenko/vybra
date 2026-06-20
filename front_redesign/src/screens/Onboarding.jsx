// src/screens/Onboarding.jsx
import React from 'react';
import { Icon } from '../components/Icon.jsx';
import { Btn, Card, CatBlock, Spark, Progress } from '../components/ui.jsx';

const ONB = [
  { kicker: 'Проблема', title: <>В избранном —<br/>десятки товаров</>,
    body: 'Списки WB и Ozon разрослись. Что из этого реально нужно, а что — импульс? Непонятно.' },
  { kicker: 'Идея', title: <>Выбра спрашивает<br/>парами</>,
    body: 'Показываем два товара. Тапни тот, что хочется сильнее. Десятки маленьких выборов вместо одного сложного.' },
  { kicker: 'Метод', title: <>Под капотом —<br/>ELO-рейтинг</>,
    body: 'Как в шахматах. Чаще побеждает — выше балл. Так всплывает то, что хочется по-настоящему.' },
  { kicker: 'Польза', title: <>И всё это —<br/>в рамках бюджета</>,
    body: 'Скажи, сколько готов потратить. Покажем, что из топа реально влезает прямо сейчас.' },
];

export function Onboarding({ t, step, wide, onNext, onBack, onSkip }) {
  const d = ONB[step - 1];
  const visual = (
    <div style={{ position: 'relative', height: '100%', minHeight: wide ? 280 : 0 }}>
      {step === 1 && <OnbPile t={t} />}
      {step === 2 && <OnbVS t={t} />}
      {step === 3 && <OnbElo t={t} />}
      {step === 4 && <OnbBudget t={t} />}
    </div>
  );
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: wide ? '8px 4px 4px' : '4px 22px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flex: '0 0 auto' }}>
        <span style={{ fontFamily: t.mono, fontSize: 11, color: t.ink3, letterSpacing: '0.06em' }}>{String(step).padStart(2, '0')} — 04</span>
        <button onClick={onSkip} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontFamily: t.font, fontSize: 12, color: t.ink3 }}>пропустить</button>
      </div>

      <div style={{ flex: 1, display: wide ? 'grid' : 'flex', flexDirection: 'column',
        gridTemplateColumns: wide ? '1fr 1fr' : undefined, gap: wide ? 40 : 0, alignItems: wide ? 'center' : 'stretch' }}>
        <div style={{ marginTop: wide ? 0 : 26, flex: '0 0 auto' }}>
          <div style={{ fontFamily: t.mono, fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase', color: t.hi, marginBottom: 14 }}>{d.kicker}</div>
          <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: wide ? 44 : 32, lineHeight: 1.04, letterSpacing: t.tight, color: t.ink }}>{d.title}</div>
          <div style={{ fontFamily: t.font, fontSize: wide ? 16 : 14, lineHeight: 1.5, color: t.ink2, marginTop: 16, maxWidth: 340 }}>{d.body}</div>
        </div>
        <div style={{ flex: wide ? '0 0 auto' : 1, position: 'relative', margin: wide ? 0 : '18px 0' }}>{visual}</div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flex: '0 0 auto', marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {[1, 2, 3, 4].map((i) => (
            <span key={i} style={{ height: 4, borderRadius: 99, transition: 'width .3s, background .3s', width: i === step ? 22 : 6, background: i <= step ? t.ink : t.hair }} />
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {onBack ? <Btn t={t} variant="outline" onClick={onBack} style={{ padding: '13px 15px' }}><Icon name="arrowL" size={18} color={t.ink} /></Btn> : null}
          <Btn t={t} variant="primary" onClick={onNext} style={{ padding: '13px 22px' }}>
            {step === 4 ? 'Подключить источники' : 'Дальше'} <Icon name="arrow" size={18} color={t.bg} />
          </Btn>
        </div>
      </div>
    </div>
  );
}

function OnbPile({ t }) {
  const cats = ['shoes', 'hoodie', 'lamp', 'book', 'mug', 'kettle'];
  const rot = [-7, 4, -3, 6, -5, 3];
  return (
    <div style={{ position: 'relative', height: '100%', minHeight: 230 }}>
      {cats.map((c, i) => (
        <div key={i} style={{ position: 'absolute', left: 6 + (i % 3) * 92, top: 6 + Math.floor(i / 3) * 108, width: 80, height: 96, transform: `rotate(${rot[i]}deg)`, boxShadow: `0 8px 18px -8px rgba(0,0,0,${t.dark ? 0.5 : 0.22})`, borderRadius: t.radiusSm }}>
          <CatBlock cat={c} t={t} iconSize={30} style={{ width: '100%', height: '100%' }} />
        </div>
      ))}
      <div style={{ position: 'absolute', right: 0, bottom: 6, display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 34, color: t.hi, letterSpacing: t.tight }}>42</span>
        <span style={{ fontFamily: t.font, fontSize: 13, color: t.ink2 }}>в избранном</span>
      </div>
    </div>
  );
}
function OnbVS({ t }) {
  return (
    <div style={{ position: 'relative', height: '100%', minHeight: 200, display: 'flex', alignItems: 'center', gap: 12 }}>
      <CatBlock cat="shoes" t={t} iconSize={44} style={{ flex: 1, height: 180, transform: 'rotate(-2deg)' }} store="WB" />
      <CatBlock cat="headphones" t={t} iconSize={44} style={{ flex: 1, height: 180, transform: 'rotate(2deg)' }} store="OZON" />
      <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', width: 46, height: 46, borderRadius: '50%', background: t.surface, color: t.ink, boxShadow: `inset 0 0 0 ${t.borderW}px ${t.ink}, 0 6px 16px -6px rgba(0,0,0,.3)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: t.font, fontWeight: t.hWeight, fontSize: 15, letterSpacing: '0.02em' }}>VS</div>
    </div>
  );
}
function OnbElo({ t }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Card t={t} style={{ padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontFamily: t.font, fontWeight: 600, fontSize: 14, color: t.ink }}>Кроссовки NB 530</span>
          <span style={{ fontFamily: t.mono, fontSize: 18, fontWeight: 600, color: t.hi, fontVariantNumeric: 'tabular-nums' }}>1 412</span>
        </div>
        <div style={{ marginTop: 10 }}>
          <Spark t={t} w={250} h={56} data={[1200, 1188, 1210, 1240, 1228, 1276, 1300, 1336, 1360, 1392, 1378, 1412]} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
          <span style={{ fontFamily: t.mono, fontSize: 10.5, color: t.ink3 }}>старт 1200</span>
          <span style={{ fontFamily: t.mono, fontSize: 10.5, color: t.good }}>+212 за 12 побед</span>
        </div>
      </Card>
    </div>
  );
}
function OnbBudget({ t }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 10 }}>
      <Card t={t} style={{ padding: 16 }}>
        <div style={{ fontFamily: t.font, fontSize: 12, color: t.ink2 }}>Бюджет</div>
        <div style={{ fontFamily: t.font, fontWeight: t.hWeight, fontSize: 30, letterSpacing: t.tight, color: t.ink, marginTop: 2 }}>15 000 ₽</div>
        <div style={{ marginTop: 12 }}><Progress t={t} value={62} color={t.accent} /></div>
      </Card>
      <Card t={t} hi style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
        <CatBlock cat="shoes" t={t} iconSize={22} style={{ width: 40, height: 40 }} />
        <div style={{ flex: 1, fontFamily: t.font, fontSize: 12.5, color: t.ink, lineHeight: 1.3 }}>NB 530 + «Дзен и искусство»</div>
        <span style={{ fontFamily: t.mono, fontSize: 12, color: t.good }}>9 780 ₽</span>
      </Card>
    </div>
  );
}
