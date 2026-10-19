// Single entry point the UI uses. Mock mode is the default and fully local.
// Both implementations expose the SAME method names, so components never branch on mode.
import axios from 'axios';
import { apiConfig } from './apiConfig';
import { mockApi } from './mockApi';

const http = axios.create({ baseURL: apiConfig.baseUrl, timeout: 10000 });

// Real mode never falls back to mock data. Failures come back as { success:false, message }.
const realRequest = async (method, url, body) => {
  try {
    const res = await http.request({ method, url, data: body });
    return res.data;
  } catch (err) {
    const message = err.response
      ? err.response.data?.message || `Server responded with ${err.response.status}`
      : `Cannot reach backend at ${apiConfig.baseUrl}. Is the server running?`;
    return { success: false, data: null, message };
  }
};

const notImplemented = (name) => () => Promise.resolve({
  success: false, data: null,
  message: `${name} is not implemented on the backend yet. Switch to mock mode or implement this endpoint.`,
});

const realApi = {
  auth: {
    login: (email, password) => realRequest('post', '/auth/login', { email, password }),
    register: (payload) => realRequest('post', '/auth/register', payload),
    logout: () => realRequest('post', '/auth/logout'),
    currentUser: () => null,
  },
  loadState: () => realRequest('get', '/state'),
  feedback: {
    getAll: () => realRequest('get', '/feedback'),
    create: (d) => realRequest('post', '/feedback', d),
    update: (id, d) => realRequest('put', `/feedback/${id}`, d),
    remove: (id) => realRequest('delete', `/feedback/${id}`),
    importMany: (rows) => realRequest('post', '/feedback/import', { records: rows }),
  },
  workspaces: {
    getAll: () => realRequest('get', '/workspaces'),
    create: (d) => realRequest('post', '/workspaces', d),
    update: (id, d) => realRequest('put', `/workspaces/${id}`, d),
    switchTo: (id) => realRequest('post', `/workspaces/${id}/switch`),
  },
  themes: { getAll: notImplemented('Themes'), saveKeywords: (id, kw) => realRequest('put', `/themes/${id}/keywords`, { keywords: kw }) },
  prioritization: {
    getAll: () => realRequest('get', '/features'),
    create: (d) => realRequest('post', '/features', d),
    update: (id, d) => realRequest('put', `/features/${id}`, d),
    remove: (id) => realRequest('delete', `/features/${id}`),
  },
  prds: {
    getAll: () => realRequest('get', '/prds'),
    create: (d) => realRequest('post', '/prds', d),
    update: (id, d) => realRequest('put', `/prds/${id}`, d),
    remove: (id) => realRequest('delete', `/prds/${id}`),
  },
  roadmap: {
    getAll: () => realRequest('get', '/roadmap'),
    create: (d) => realRequest('post', '/roadmap', d),
    update: (id, d) => realRequest('put', `/roadmap/${id}`, d),
    remove: (id) => realRequest('delete', `/roadmap/${id}`),
  },
  dashboard: { getActivity: () => realRequest('get', '/activity') },
  preferences: { update: (d) => realRequest('put', '/preferences', d) },
  chat: {
    getHistory: () => realRequest('get', '/chat'),
    saveHistory: (msgs) => realRequest('put', '/chat', { messages: msgs }),
    clear: () => realRequest('delete', '/chat'),
  },
};

export const apiClient = apiConfig.isMock ? mockApi : realApi;
export const isMockMode = apiConfig.isMock;
