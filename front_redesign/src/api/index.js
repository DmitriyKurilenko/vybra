// src/api/index.js — единая точка входа. По умолчанию ходит в реальный API
// (same-origin). Встроенный мок включается только явным флагом VITE_USE_MOCK=true
// (для офлайн-демо без бэкенда).

import { mockApi, parsePreview as mockPreview, SAMPLE_LINKS, SEED } from './mock.js';
import { httpApi } from './client.js';

const useMock = import.meta.env.VITE_USE_MOCK === 'true';

export const api = useMock ? mockApi : httpApi;
export const IS_MOCK = useMock;

// preview: у реального API — оптимистичное по ссылке, у мока — локальная функция
export const previewUrl = useMock ? async (url) => mockPreview(url) : httpApi.preview;

export { SAMPLE_LINKS, SEED };
