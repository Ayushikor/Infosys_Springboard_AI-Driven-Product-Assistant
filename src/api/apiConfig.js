// Central API configuration. Default mode is "mock".
const mode = (import.meta.env.VITE_API_MODE || 'mock').toLowerCase();

export const apiConfig = {
  mode,
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api',
  mockDelayMs: 250,
  isMock: mode !== 'real',
};
