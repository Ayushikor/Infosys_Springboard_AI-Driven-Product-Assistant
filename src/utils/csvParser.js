// Parses CSV and JSON files entirely in the browser. Nothing is uploaded.
export const MAX_FILE_BYTES = 2 * 1024 * 1024; // 2 MB
export const ALLOWED_TYPES = ['csv', 'json'];

export const detectType = (file) => {
  const ext = file.name.split('.').pop().toLowerCase();
  return ALLOWED_TYPES.includes(ext) ? ext : null;
};

// Minimal RFC 4180-style parser: handles quoted fields, escaped quotes and embedded commas/newlines.
export const parseCsvText = (text) => {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') inQuotes = false;
      else field += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some((c) => c.trim() !== '')) rows.push(row);
      row = [];
    } else field += ch;
  }
  if (field !== '' || row.length) { row.push(field); if (row.some((c) => c.trim() !== '')) rows.push(row); }
  return rows;
};

export const REQUIRED_FIELDS = ['title', 'message'];
const normalizeHeader = (h) => h.trim().toLowerCase().replace(/\s+/g, '');

// Maps a raw object (from CSV row or JSON item) to the expected feedback shape.
export const mapRecord = (raw, index) => {
  const get = (...keys) => {
    for (const k of keys) {
      const hit = Object.keys(raw).find((rk) => normalizeHeader(rk) === k);
      if (hit !== undefined && raw[hit] !== undefined && raw[hit] !== null) return String(raw[hit]).trim();
    }
    return '';
  };
  const title = get('title', 'subject');
  const message = get('message', 'body', 'description');
  const errors = [];
  if (!title) errors.push('missing title');
  if (!message) errors.push('missing message');
  const votesRaw = get('votes', 'vote');
  const createdRaw = get('createdat', 'date', 'created');
  return {
    rowNumber: index + 1,
    errors,
    record: {
      id: get('id') || undefined,
      title, message,
      customer: get('customer', 'company', 'account') || 'Unknown',
      source: get('source', 'channel') || 'Import',
      createdAt: createdRaw && !isNaN(Date.parse(createdRaw)) ? new Date(createdRaw).toISOString() : new Date().toISOString(),
      sentiment: get('sentiment').toLowerCase() || 'neutral',
      theme: get('theme', 'category') || 'Uncategorized',
      votes: votesRaw && !isNaN(Number(votesRaw)) ? Number(votesRaw) : 0,
    },
  };
};

// Validates structure and returns { rows, fatal }. fatal = string if the whole file is unusable.
export const parseFeedbackFile = async (file) => {
  const type = detectType(file);
  if (!type) return { rows: [], fatal: 'Unsupported file type. Please upload a .csv or .json file.' };
  if (file.size === 0) return { rows: [], fatal: 'The file is empty.' };
  if (file.size > MAX_FILE_BYTES) return { rows: [], fatal: 'File is larger than 2 MB.' };

  const text = await file.text();
  let objects;
  if (type === 'csv') {
    const table = parseCsvText(text);
    if (table.length < 2) return { rows: [], fatal: 'CSV must include a header row and at least one data row.' };
    const headers = table[0];
    if (!headers.some((h) => normalizeHeader(h) === 'title') || !headers.some((h) => normalizeHeader(h) === 'message')) {
      return { rows: [], fatal: 'CSV must include "title" and "message" columns.' };
    }
    objects = table.slice(1).map((cells) => Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? ''])));
  } else {
    let parsed;
    try { parsed = JSON.parse(text); } catch { return { rows: [], fatal: 'Invalid JSON syntax.' }; }
    const arr = Array.isArray(parsed) ? parsed : parsed?.feedback;
    if (!Array.isArray(arr)) return { rows: [], fatal: 'JSON must be an array of feedback objects, or an object with a "feedback" array.' };
    if (arr.some((x) => typeof x !== 'object' || x === null)) return { rows: [], fatal: 'Every JSON item must be an object.' };
    objects = arr;
  }
  if (!objects.length) return { rows: [], fatal: 'No records found in file.' };
  return { rows: objects.map(mapRecord), fatal: null };
};
