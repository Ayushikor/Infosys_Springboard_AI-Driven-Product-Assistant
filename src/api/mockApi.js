// Frontend-only mock backend. Simulates async requests and persists to LocalStorage.
// Every response uses: { success, data, message }.
// DEMO ONLY: passwords are SHA-256 hashed in the browser. This is NOT production security.
import { apiConfig } from './apiConfig';
import {
  SEED_THEMES, SEED_FEEDBACK, SEED_FEATURES, SEED_PRDS, SEED_ROADMAP,
  SEED_WORKSPACE, SEED_ACTIVITY,
} from './mockData';

const USERS_KEY = 'copilot.users';
const SESSION_KEY = 'copilot.session';
const dataKey = (userId) => `copilot.data.${userId}`;
const uid = (p) => `${p}-${Math.random().toString(36).slice(2, 9)}${Date.now().toString(36).slice(-3)}`;
const delay = () => new Promise((r) => setTimeout(r, apiConfig.mockDelayMs));

const ok = (data, message = 'Operation completed successfully') => ({ success: true, data, message });
const fail = (message, data = null) => ({ success: false, data, message });

// ---------- storage helpers (safe against corrupt JSON and disabled storage) ----------
const read = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};
const write = (key, value) => {
  try { localStorage.setItem(key, JSON.stringify(value)); return true; }
  catch { return false; }
};

const hashPassword = async (password, salt) => {
  const buf = new TextEncoder().encode(`${salt}:${password}`);
  const digest = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
};
const newSalt = () => crypto.getRandomValues(new Uint8Array(16)).reduce((s, b) => s + b.toString(16).padStart(2, '0'), '');

const validateEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
const validatePassword = (p) => {
  if (p.length < 8) return 'Password must be at least 8 characters.';
  if (!/[A-Z]/.test(p)) return 'Password must include an uppercase letter.';
  if (!/[a-z]/.test(p)) return 'Password must include a lowercase letter.';
  if (!/[0-9]/.test(p)) return 'Password must include a number.';
  return null;
};
const sanitizeUser = (u) => ({ id: u.id, username: u.username, email: u.email, name: u.name, role: u.role, createdAt: u.createdAt });

// ---------- seeding ----------
// The demo account gets the full sample dataset; new registrations start empty.
const seedDemoData = () => ({
  themes: SEED_THEMES,
  feedback: SEED_FEEDBACK,
  features: SEED_FEATURES,
  prds: SEED_PRDS,
  roadmap: SEED_ROADMAP,
  workspaces: [SEED_WORKSPACE],
  activeWorkspaceId: SEED_WORKSPACE.id,
  activity: SEED_ACTIVITY,
  chat: [],
  preferences: { theme: 'light', compactTables: false },
});

const emptyUserData = (user) => {
  const ws = {
    id: uid('ws'),
    name: `${user.name.split(' ')[0]}'s Workspace`,
    description: 'Describe what this workspace is for.',
    createdAt: new Date().toISOString(),
  };
  return {
    themes: SEED_THEMES, // theme definitions are generic; counts come from feedback
    feedback: [], features: [], prds: [], roadmap: [],
    workspaces: [ws], activeWorkspaceId: ws.id,
    activity: [{ id: uid('act'), text: 'Workspace created', at: new Date().toISOString() }],
    chat: [],
    preferences: { theme: 'light', compactTables: false },
  };
};

const ensureDemoUser = async () => {
  const users = read(USERS_KEY, null);
  if (users && users.length) return;
  const salt = newSalt();
  const demo = {
    id: 'usr-demo',
    username: 'admin',
    email: 'admin@copilot.com',
    name: 'Alex Morgan',
    role: 'Product Manager',
    createdAt: new Date().toISOString(),
    salt,
    passwordHash: await hashPassword('Admin123!', salt),
  };
  write(USERS_KEY, [demo]);
  write(dataKey(demo.id), seedDemoData());
};

const getUsers = () => read(USERS_KEY, []);
const getCurrentUserRecord = () => {
  const session = read(SESSION_KEY, null);
  if (!session) return null;
  return getUsers().find((u) => u.id === session.userId) || null;
};

// Per-user data store. Every mutation goes through saveData so LocalStorage stays in sync.
const loadData = (userId) => read(dataKey(userId), null);
const saveData = (userId, data) => write(dataKey(userId), data);
const withData = (fn) => {
  const user = getCurrentUserRecord();
  if (!user) return fail('Not authenticated. Please log in.');
  const data = loadData(user.id);
  if (!data) return fail('Workspace data not found.');
  return fn(data, user);
};
const logActivity = (data, text) => {
  data.activity = [{ id: uid('act'), text, at: new Date().toISOString() }, ...data.activity].slice(0, 50);
};

// ---------- auth ----------
const auth = {
  async login(email, password, remember = false) {
    await delay();
    await ensureDemoUser();
    const normalized = (email || '').trim().toLowerCase();
    if (!validateEmail(normalized)) return fail('Enter a valid email address.');
    if (!password) return fail('Password is required.');
    const user = getUsers().find((u) => u.email === normalized);
    if (!user) return fail('No account found with that email. Please register first.');
    const hash = await hashPassword(password, user.salt);
    if (hash !== user.passwordHash) return fail('Incorrect password.');
    const session = { userId: user.id, remember, createdAt: new Date().toISOString() };
    write(SESSION_KEY, session);
    return ok({ user: sanitizeUser(user) }, 'Logged in successfully');
  },

  async register({ name, username, email, password, confirmPassword, role }) {
    await delay();
    await ensureDemoUser();
    const normalizedEmail = (email || '').trim().toLowerCase();
    const cleanUsername = (username || '').trim();
    const cleanName = (name || '').trim();
    const errors = {};
    if (!cleanName || cleanName.length < 2) errors.name = 'Full name must be at least 2 characters.';
    if (!/^[a-zA-Z0-9_]{3,20}$/.test(cleanUsername)) errors.username = 'Username: 3–20 letters, numbers or underscores.';
    if (!validateEmail(normalizedEmail)) errors.email = 'Enter a valid email address.';
    const pwError = validatePassword(password || '');
    if (pwError) errors.password = pwError;
    if (password !== confirmPassword) errors.confirmPassword = 'Passwords do not match.';
    if (Object.keys(errors).length) return { success: false, data: { errors }, message: 'Please fix the highlighted fields.' };

    const users = getUsers();
    if (users.some((u) => u.email === normalizedEmail)) return { success: false, data: { errors: { email: 'This email is already registered.' } }, message: 'Email already registered.' };
    if (users.some((u) => u.username.toLowerCase() === cleanUsername.toLowerCase())) return { success: false, data: { errors: { username: 'This username is taken.' } }, message: 'Username taken.' };

    const salt = newSalt();
    const user = {
      id: uid('usr'),
      username: cleanUsername,
      email: normalizedEmail,
      name: cleanName,
      role: role || 'Product Manager',
      createdAt: new Date().toISOString(),
      salt,
      passwordHash: await hashPassword(password, salt),
    };
    write(USERS_KEY, [...users, user]);
    write(dataKey(user.id), emptyUserData(user));
    return ok({ user: sanitizeUser(user) }, 'Account created. You can now sign in.');
  },

  async logout() {
    await delay();
    try { localStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
    return ok(null, 'Logged out');
  },

  // Synchronous read used by AuthContext on boot.
  currentUser() {
    const user = getCurrentUserRecord();
    return user ? sanitizeUser(user) : null;
  },
};

// ---------- feedback ----------
const feedback = {
  getAll: async () => { await delay(); return withData((d) => ok(d.feedback)); },
  async create(payload) {
    await delay();
    return withData((d, user) => {
      const err = validateFeedback(payload);
      if (err) return fail(err);
      const record = normalizeFeedback({ ...payload, id: uid('fb') });
      d.feedback = [record, ...d.feedback];
      logActivity(d, `Feedback "${record.title}" added`);
      saveData(user.id, d);
      return ok(record, 'Feedback created');
    });
  },
  async update(id, patch) {
    await delay();
    return withData((d, user) => {
      const idx = d.feedback.findIndex((f) => f.id === id);
      if (idx === -1) return fail('Feedback not found.');
      d.feedback[idx] = normalizeFeedback({ ...d.feedback[idx], ...patch, id });
      logActivity(d, `Feedback "${d.feedback[idx].title}" updated`);
      saveData(user.id, d);
      return ok(d.feedback[idx], 'Feedback updated');
    });
  },
  async remove(id) {
    await delay();
    return withData((d, user) => {
      const target = d.feedback.find((f) => f.id === id);
      if (!target) return fail('Feedback not found.');
      d.feedback = d.feedback.filter((f) => f.id !== id);
      logActivity(d, `Feedback "${target.title}" deleted`);
      saveData(user.id, d);
      return ok({ id }, 'Feedback deleted');
    });
  },
  // Bulk insert used by the upload module. Returns counts so the UI can report honestly.
  async importMany(records) {
    await delay();
    return withData((d, user) => {
      const existingIds = new Set(d.feedback.map((f) => f.id));
      const toAdd = records.map((r) => normalizeFeedback(r)).filter((r) => !existingIds.has(r.id));
      d.feedback = [...toAdd, ...d.feedback];
      logActivity(d, `Imported ${toAdd.length} feedback record(s)`);
      saveData(user.id, d);
      return ok({ added: toAdd.length, skipped: records.length - toAdd.length }, `Imported ${toAdd.length} record(s)`);
    });
  },
};

const validateFeedback = (f) => {
  if (!f || !f.title || !String(f.title).trim()) return 'Title is required.';
  if (!f.message || !String(f.message).trim()) return 'Message is required.';
  return null;
};

const SENTIMENTS = ['positive', 'neutral', 'negative'];
const normalizeFeedback = (f) => ({
  id: f.id || uid('fb'),
  title: String(f.title || '').trim(),
  message: String(f.message || '').trim(),
  customer: String(f.customer || 'Unknown').trim() || 'Unknown',
  source: String(f.source || 'Manual').trim() || 'Manual',
  createdAt: f.createdAt && !isNaN(Date.parse(f.createdAt)) ? new Date(f.createdAt).toISOString() : new Date().toISOString(),
  sentiment: SENTIMENTS.includes(String(f.sentiment).toLowerCase()) ? String(f.sentiment).toLowerCase() : 'neutral',
  theme: String(f.theme || 'Uncategorized').trim() || 'Uncategorized',
  votes: Number.isFinite(Number(f.votes)) ? Math.max(0, Math.round(Number(f.votes))) : 0,
});

// ---------- workspaces ----------
const workspaces = {
  async getAll() { await delay(); return withData((d) => ok({ items: d.workspaces, activeId: d.activeWorkspaceId })); },
  async create({ name, description }) {
    await delay();
    return withData((d, user) => {
      if (!name || name.trim().length < 2) return fail('Workspace name must be at least 2 characters.');
      const ws = { id: uid('ws'), name: name.trim(), description: (description || '').trim(), createdAt: new Date().toISOString() };
      d.workspaces = [...d.workspaces, ws];
      d.activeWorkspaceId = ws.id;
      logActivity(d, `Workspace "${ws.name}" created`);
      saveData(user.id, d);
      return ok(ws, 'Workspace created');
    });
  },
  async update(id, { name, description }) {
    await delay();
    return withData((d, user) => {
      const ws = d.workspaces.find((w) => w.id === id);
      if (!ws) return fail('Workspace not found.');
      if (name !== undefined && name.trim().length < 2) return fail('Workspace name must be at least 2 characters.');
      if (name !== undefined) ws.name = name.trim();
      if (description !== undefined) ws.description = description.trim();
      logActivity(d, `Workspace "${ws.name}" updated`);
      saveData(user.id, d);
      return ok(ws, 'Workspace updated');
    });
  },
  async switchTo(id) {
    await delay();
    return withData((d, user) => {
      if (!d.workspaces.some((w) => w.id === id)) return fail('Workspace not found.');
      d.activeWorkspaceId = id;
      saveData(user.id, d);
      return ok({ activeId: id }, 'Workspace switched');
    });
  },
};

// ---------- themes (analysis lives in utils/themeAnalyzer; this is persistence) ----------
const themes = {
  getAll: async () => { await delay(); return withData((d) => ok(d.themes)); },
  async saveKeywords(id, keywords) {
    await delay();
    return withData((d, user) => {
      const t = d.themes.find((x) => x.id === id);
      if (!t) return fail('Theme not found.');
      t.keywords = keywords;
      saveData(user.id, d);
      return ok(t, 'Theme keywords saved');
    });
  },
};

// ---------- prioritization ----------
const prioritization = {
  getAll: async () => { await delay(); return withData((d) => ok(d.features)); },
  async create(payload) {
    await delay();
    return withData((d, user) => {
      const f = { ...normalizeFeature(payload), id: uid('ft') };
      d.features = [...d.features, f];
      logActivity(d, `Feature "${f.name}" added`);
      saveData(user.id, d);
      return ok(f, 'Feature created');
    });
  },
  async update(id, patch) {
    await delay();
    return withData((d, user) => {
      const idx = d.features.findIndex((f) => f.id === id);
      if (idx === -1) return fail('Feature not found.');
      d.features[idx] = { ...normalizeFeature({ ...d.features[idx], ...patch }), id };
      logActivity(d, `Feature "${d.features[idx].name}" updated`);
      saveData(user.id, d);
      return ok(d.features[idx], 'Feature updated');
    });
  },
  async remove(id) {
    await delay();
    return withData((d, user) => {
      const f = d.features.find((x) => x.id === id);
      if (!f) return fail('Feature not found.');
      d.features = d.features.filter((x) => x.id !== id);
      logActivity(d, `Feature "${f.name}" deleted`);
      saveData(user.id, d);
      return ok({ id }, 'Feature deleted');
    });
  },
};

const normalizeFeature = (f) => ({
  name: String(f.name || '').trim(),
  theme: f.theme || 'Uncategorized',
  reach: Math.max(0, Number(f.reach) || 0),
  impact: Math.min(3, Math.max(0.25, Number(f.impact) || 1)),
  confidence: Math.min(1, Math.max(0, Number(f.confidence) || 0)),
  effort: Math.max(0.1, Number(f.effort) || 1),
  status: f.status || 'Backlog',
  description: f.description || '',
});

// ---------- PRDs ----------
const prds = {
  getAll: async () => { await delay(); return withData((d) => ok(d.prds)); },
  async create(payload) {
    await delay();
    return withData((d, user) => {
      const p = { id: uid('prd'), version: '0.1', status: 'Draft', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), content: null, ...payload };
      d.prds = [...d.prds, p];
      logActivity(d, `PRD "${p.title}" created`);
      saveData(user.id, d);
      return ok(p, 'PRD created');
    });
  },
  async update(id, patch) {
    await delay();
    return withData((d, user) => {
      const idx = d.prds.findIndex((p) => p.id === id);
      if (idx === -1) return fail('PRD not found.');
      d.prds[idx] = { ...d.prds[idx], ...patch, updatedAt: new Date().toISOString() };
      logActivity(d, `PRD "${d.prds[idx].title}" updated`);
      saveData(user.id, d);
      return ok(d.prds[idx], 'PRD saved');
    });
  },
  async remove(id) {
    await delay();
    return withData((d, user) => {
      d.prds = d.prds.filter((p) => p.id !== id);
      saveData(user.id, d);
      return ok({ id }, 'PRD deleted');
    });
  },
};

// ---------- roadmap ----------
const roadmap = {
  getAll: async () => { await delay(); return withData((d) => ok(d.roadmap)); },
  async create(payload) {
    await delay();
    return withData((d, user) => {
      if (!payload.name) return fail('Name is required.');
      if (payload.startDate && payload.targetDate && payload.targetDate < payload.startDate) return fail('Target date cannot be before start date.');
      const item = { id: uid('rm'), priority: 'Medium', status: 'Planned', owner: 'Unassigned', ...payload };
      d.roadmap = [...d.roadmap, item];
      logActivity(d, `Roadmap item "${item.name}" added`);
      saveData(user.id, d);
      return ok(item, 'Roadmap item created');
    });
  },
  async update(id, patch) {
    await delay();
    return withData((d, user) => {
      const idx = d.roadmap.findIndex((r) => r.id === id);
      if (idx === -1) return fail('Roadmap item not found.');
      const next = { ...d.roadmap[idx], ...patch };
      if (next.startDate && next.targetDate && next.targetDate < next.startDate) return fail('Target date cannot be before start date.');
      d.roadmap[idx] = next;
      logActivity(d, `Roadmap item "${next.name}" updated`);
      saveData(user.id, d);
      return ok(next, 'Roadmap item updated');
    });
  },
  async remove(id) {
    await delay();
    return withData((d, user) => {
      d.roadmap = d.roadmap.filter((r) => r.id !== id);
      saveData(user.id, d);
      return ok({ id }, 'Roadmap item deleted');
    });
  },
};

// ---------- dashboard / activity / preferences / chat ----------
const dashboard = {
  async getActivity() { await delay(); return withData((d) => ok(d.activity)); },
};

const preferences = {
  async update(patch) {
    await delay();
    return withData((d, user) => {
      d.preferences = { ...d.preferences, ...patch };
      saveData(user.id, d);
      return ok(d.preferences, 'Preferences saved');
    });
  },
};

const chat = {
  async getHistory() { await delay(); return withData((d) => ok(d.chat)); },
  async saveHistory(messages) {
    return withData((d, user) => { d.chat = messages; saveData(user.id, d); return ok(messages); });
  },
  async clear() {
    return withData((d, user) => { d.chat = []; saveData(user.id, d); return ok([], 'Conversation cleared'); });
  },
};

export const mockApi = {
  auth, feedback, workspaces, themes, prioritization, prds, roadmap, dashboard, preferences, chat,
  // Used by context providers to load full state in one call.
  async loadState() {
    await delay();
    return withData((d) => ok(d));
  },
  // Exposed for seeding checks and tests.
  _internal: { ensureDemoUser, getCurrentUserRecord },
};

// Ensure the demo account exists on module load.
ensureDemoUser().catch(() => {});
