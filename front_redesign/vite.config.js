import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
//
// Доставка: single-origin. Vite собирает SPA в `dist`, Django/WhiteNoise отдаёт
// ассеты под префиксом `/static/spa/`, а саму оболочку `index.html` — catch-all
// view Django. Поэтому `base` указывает на публичный URL статики, а не на корень.
export default defineConfig({
  plugins: [react()],
  base: '/static/spa/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    // Ассеты Vite уже контентно-хешируются — иммутабельный кэш на стороне WhiteNoise.
    assetsDir: 'assets',
  },
  server: { port: 5173 },
});
