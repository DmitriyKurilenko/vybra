// src/components/Icon.jsx — линейные иконки одним компонентом.
import React from 'react';

export function Icon({ name, size = 20, color = 'currentColor', sw = 1.6, style }) {
  const p = {
    width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: color, strokeWidth: sw, strokeLinecap: 'round', strokeLinejoin: 'round',
    style: { display: 'block', ...style },
  };
  switch (name) {
    case 'plus':    return <svg {...p}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>;
    case 'check':   return <svg {...p}><polyline points="4,12.5 9.5,18 20,6"/></svg>;
    case 'cross':   return <svg {...p}><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>;
    case 'arrow':   return <svg {...p}><line x1="4" y1="12" x2="19" y2="12"/><polyline points="13,6 19,12 13,18"/></svg>;
    case 'arrowL':  return <svg {...p}><line x1="20" y1="12" x2="5" y2="12"/><polyline points="11,6 5,12 11,18"/></svg>;
    case 'chevR':   return <svg {...p}><polyline points="9,5 16,12 9,19"/></svg>;
    case 'search':  return <svg {...p}><circle cx="11" cy="11" r="6"/><line x1="15.5" y1="15.5" x2="20" y2="20"/></svg>;
    case 'star':    return <svg {...p}><polygon points="12,3 14.6,9 21,9.6 16,14 17.5,20.5 12,17 6.5,20.5 8,14 3,9.6 9.4,9"/></svg>;
    case 'trash':   return <svg {...p}><polyline points="4,7 20,7"/><path d="M7 7l1 13h8l1-13"/><line x1="10" y1="4" x2="14" y2="4"/></svg>;
    case 'sun':     return <svg {...p}><circle cx="12" cy="12" r="4.2"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="5" y1="5" x2="7" y2="7"/><line x1="17" y1="17" x2="19" y2="19"/><line x1="19" y1="5" x2="17" y2="7"/><line x1="7" y1="17" x2="5" y2="19"/></svg>;
    case 'moon':    return <svg {...p}><path d="M20 14.5A8 8 0 0 1 9.5 4 7 7 0 1 0 20 14.5Z"/></svg>;
    case 'reset':   return <svg {...p}><path d="M4 12a8 8 0 1 0 2.5-5.8"/><polyline points="3,3 3,8 8,8"/></svg>;
    case 'link':    return <svg {...p}><path d="M9 15l6-6"/><path d="M10.5 6.5l1.5-1.5a4 4 0 0 1 5.7 5.7l-2.2 2.2"/><path d="M13.5 17.5l-1.5 1.5a4 4 0 0 1-5.7-5.7l2.2-2.2"/></svg>;
    case 'trophy':  return <svg {...p}><path d="M7 4h10v4a5 5 0 0 1-10 0Z"/><path d="M7 6H4v1a3 3 0 0 0 3 3"/><path d="M17 6h3v1a3 3 0 0 1-3 3"/><line x1="12" y1="13" x2="12" y2="17"/><path d="M8.5 20h7l-1-3h-5Z"/></svg>;
    case 'heart':   return <svg {...p}><path d="M12 20S4 14.5 4 9.2A3.8 3.8 0 0 1 12 7a3.8 3.8 0 0 1 8 2.2C20 14.5 12 20 12 20Z"/></svg>;
    case 'user':    return <svg {...p}><circle cx="12" cy="8.5" r="3.8"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>;
    case 'cards':   return <svg {...p}><rect x="4" y="5" width="7" height="14" rx="1.5"/><rect x="13" y="5" width="7" height="14" rx="1.5"/></svg>;
    case 'wallet':  return <svg {...p}><rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18"/><circle cx="16.5" cy="14.5" r="1.2" fill={color} stroke="none"/></svg>;
    // категории
    case 'shoe':    return <svg {...p}><path d="M3 15v-4l5-1 3 3 7 1a3 3 0 0 1 3 3v2H4Z"/><path d="M8 10l1.5 2"/></svg>;
    case 'shirt':   return <svg {...p}><path d="M8 4 5 6 3 9l2.5 2 1-1V20h11V10l1 1L21 9 19 6 16 4a2.5 2.5 0 0 1-8 0Z"/></svg>;
    case 'lamp':    return <svg {...p}><path d="M8 4h8l2.5 7h-13Z"/><line x1="12" y1="11" x2="12" y2="19"/><line x1="9" y1="20" x2="15" y2="20"/></svg>;
    case 'kettle':  return <svg {...p}><path d="M6 9h11a4 4 0 0 1 4 4v3a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3Z"/><path d="M6 12H3l2-3"/><line x1="10" y1="6" x2="15" y2="6"/></svg>;
    case 'book':    return <svg {...p}><path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2Z"/><line x1="9" y1="4" x2="9" y2="20"/></svg>;
    case 'mug':     return <svg {...p}><path d="M5 7h11v8a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4Z"/><path d="M16 9h2.5a2.5 2.5 0 0 1 0 5H16"/></svg>;
    case 'tablet':  return <svg {...p}><rect x="6" y="3" width="12" height="18" rx="2.5"/><line x1="10.5" y1="18" x2="13.5" y2="18"/></svg>;
    case 'candle':  return <svg {...p}><rect x="9" y="9" width="6" height="11" rx="1"/><path d="M12 9V6"/><path d="M12 6c1.2-1.2 1.2-2.5 0-4-1.2 1.5-1.2 2.8 0 4Z" fill={color} stroke="none"/></svg>;
    case 'socks':   return <svg {...p}><path d="M9 3v8l-3.5 4a3.5 3.5 0 0 0 5 5l5-5a3 3 0 0 0 1-2.3V3Z"/></svg>;
    case 'headphones': return <svg {...p}><path d="M5 14v-2a7 7 0 0 1 14 0v2"/><rect x="3.5" y="13" width="4" height="6" rx="1.6"/><rect x="16.5" y="13" width="4" height="6" rx="1.6"/></svg>;
    case 'box':     return <svg {...p}><path d="M4 8 12 4l8 4v8l-8 4-8-4Z"/><path d="M4 8l8 4 8-4"/><line x1="12" y1="12" x2="12" y2="20"/></svg>;
    default:        return null;
  }
}
