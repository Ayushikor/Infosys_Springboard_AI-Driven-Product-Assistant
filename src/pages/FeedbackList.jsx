import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Pencil, Trash2, Eye, Upload, MessageSquareText, AlertTriangle } from 'lucide-react';
import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';
import { analyzeThemes } from '../utils/themeAnalyzer';
import { formatDate } from '../utils/formatters';
import DataTable from '../components/common/DataTable';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const PAGE_SIZE = 8;
const SENTIMENTS = ['positive', 'neutral', 'negative'];

export default function FeedbackList() {
  const { raw, loading, error, refresh } = useAppData();
  const [query, setQuery] = useState('');
  const [sentiment, setSentiment] = useState('');
  const [theme, setTheme] = useState('');
  const [source, setSource] = useState('');
  const [sortKey, setSortKey] = useState('createdAt');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(new Set());
  const [viewing, setViewing] = useState(null);
  const [editing, setEditing] = useState(null);
  const [confirm, setConfirm] = useState(null); // { ids, label }
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  // Use the same theme assignment logic as the Themes page so labels always match.
  const withThemes = useMemo(() => {
    if (!raw) return [];
    const analyzed = analyzeThemes(raw.feedback, raw.themes);
    const map = new Map();
    analyzed.forEach((t) => t.items.forEach((f) => map.set(f.id, t.name)));
    return raw.feedback.map((f) => ({ ...f, displayTheme: map.get(f.id) || f.theme }));
  }, [raw]);

  const sources = useMemo(() => [...new Set(withThemes.map((f) => f.source))].sort(), [withThemes]);
  const themeNames = useMemo(() => (raw?.themes || []).map((t) => t.name), [raw]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return withThemes
      .filter((f) => !q || f.title.toLowerCase().includes(q) || f.message.toLowerCase().includes(q))
      .filter((f) => !sentiment || f.sentiment === sentiment)
      .filter((f) => !theme || f.displayTheme === theme)
      .filter((f) => !source || f.source === source)
      .sort((a, b) => {
        const av = a[sortKey], bv = b[sortKey];
        const cmp = sortKey === 'createdAt' ? new Date(av) - new Date(bv) : typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv));
        return sortDir === 'asc' ? cmp : -cmp;
      });
  }, [withThemes, query, sentiment, theme, source, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const pageIds = pageRows.map((r) => r.id);
  const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));

  const onSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('asc'); }
  };

  const toggleOne = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const togglePage = () => setSelected((s) => {
    const n = new Set(s);
    if (allOnPageSelected) pageIds.forEach((id) => n.delete(id));
    else pageIds.forEach((id) => n.add(id));
    return n;
  });

  const runDelete = async () => {
    setBusy(true);
    const ids = confirm.ids;
    const results = await Promise.all(ids.map((id) => apiClient.feedback.remove(id)));
    setBusy(false);
    const failed = results.filter((r) => !r.success).length;
    setConfirm(null);
    setSelected(new Set());
    await refresh();
    setToast(failed ? { type: 'error', text: `${failed} record(s) could not be deleted.` } : { type: 'success', text: `Deleted ${ids.length} record(s).` });
  };

  const saveEdit = async (patch) => {
    setBusy(true);
    const res = await apiClient.feedback.update(editing.id, patch);
    setBusy(false);
    if (res.success) { setEditing(null); await refresh(); setToast({ type: 'success', text: 'Feedback updated.' }); }
    else setToast({ type: 'error', text: res.message });
  };

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load feedback" description={error} action={<Button variant="outline" onClick={refresh}>Retry</Button>} />;

  const columns = [
    {
      key: 'select', label: <input type="checkbox" aria-label="Select all on this page" checked={allOnPageSelected} onChange={togglePage} className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent" />,
      render: (r) => <input type="checkbox" aria-label={`Select ${r.title}`} checked={selected.has(r.id)} onChange={() => toggleOne(r.id)} className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent" />,
    },
    { key: 'title', label: 'Title', sortable: true, render: (r) => <span className="block max-w-[220px] truncate font-medium">{r.title}</span> },
    { key: 'customer', label: 'Customer', sortable: true, render: (r) => <span className="text-navy-500">{r.customer}</span> },
    { key: 'message', label: 'Message', render: (r) => <span className="block max-w-[260px] truncate text-navy-500">{r.message}</span> },
    { key: 'source', label: 'Source', sortable: true, render: (r) => <span className="whitespace-nowrap text-navy-500">{r.source}</span> },
    { key: 'displayTheme', label: 'Theme', sortable: true, render: (r) => <span className="whitespace-nowrap">{r.displayTheme}</span> },
    { key: 'sentiment', label: 'Sentiment', sortable: true, render: (r) => <Badge tone={r.sentiment}>{r.sentiment}</Badge> },
    { key: 'votes', label: 'Votes', sortable: true, render: (r) => <span className="tabular-nums">{r.votes}</span> },
    { key: 'createdAt', label: 'Date', sortable: true, render: (r) => <span className="whitespace-nowrap text-navy-500">{formatDate(r.createdAt)}</span> },
    {
      key: 'actions', label: 'Actions',
      render: (r) => (
        <div className="flex gap-1">
          <button className="btn-ghost p-1.5" onClick={() => setViewing(r)} aria-label={`View ${r.title}`}><Eye size={15} /></button>
          <button className="btn-ghost p-1.5" onClick={() => setEditing(r)} aria-label={`Edit ${r.title}`}><Pencil size={15} /></button>
          <button className="btn-ghost p-1.5 hover:text-rose-600" onClick={() => setConfirm({ ids: [r.id], label: r.title })} aria-label={`Delete ${r.title}`}><Trash2 size={15} /></button>
        </div>
      ),
    },
  ];

  if (!raw.feedback.length) {
    return (
      <EmptyState
        icon={MessageSquareText}
        title="No feedback yet"
        description="Import a CSV or JSON file to populate this list."
        action={<Link to="/feedback/upload" className="btn-primary"><Upload size={16} />Upload feedback</Link>}
      />
    );
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div role="status" className={`flex items-center justify-between rounded-lg border p-3 text-sm ${toast.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
          {toast.text}
          <button onClick={() => setToast(null)} className="text-xs underline">Dismiss</button>
        </div>
      )}

      {/* Filters */}
      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-[34px] text-navy-500" />
          <input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Search title or message" className="input pl-9" aria-label="Search feedback" />
        </div>
        <FilterSelect label="Sentiment" value={sentiment} onChange={(v) => { setSentiment(v); setPage(1); }} options={SENTIMENTS} />
        <FilterSelect label="Theme" value={theme} onChange={(v) => { setTheme(v); setPage(1); }} options={themeNames} />
        <FilterSelect label="Source" value={source} onChange={(v) => { setSource(v); setPage(1); }} options={sources} />
      </div>

      {/* Bulk bar */}
      {selected.size > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-indigo-50 px-4 py-2.5 text-sm dark:bg-indigo-500/10">
          <span><strong>{selected.size}</strong> selected</span>
          <div className="flex gap-2">
            <button className="btn-ghost text-xs" onClick={() => setSelected(new Set())}>Clear</button>
            <Button variant="danger" className="!py-1.5 text-xs" onClick={() => setConfirm({ ids: [...selected], label: `${selected.size} records` })}><Trash2 size={14} />Delete selected</Button>
          </div>
        </div>
      )}

      <div className="card overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState icon={Search} title="No matching feedback" description="Try clearing a filter or changing your search." action={<Button variant="outline" onClick={() => { setQuery(''); setSentiment(''); setTheme(''); setSource(''); }}>Clear filters</Button>} />
        ) : (
          <DataTable
            columns={columns}
            rows={pageRows}
            rowKey={(r) => r.id}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={onSort}
          />
        )}
        {filtered.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm dark:border-navy-700">
            <span className="text-navy-500">Showing {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filtered.length)} of {filtered.length}</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" className="!px-3 !py-1.5" disabled={safePage === 1} onClick={() => setPage(safePage - 1)}>Previous</Button>
              <span className="tabular-nums text-navy-500">{safePage} / {pageCount}</span>
              <Button variant="outline" className="!px-3 !py-1.5" disabled={safePage === pageCount} onClick={() => setPage(safePage + 1)}>Next</Button>
            </div>
          </div>
        )}
      </div>

      {/* View modal */}
      <Modal open={!!viewing} onClose={() => setViewing(null)} title="Feedback details" footer={<Button variant="outline" onClick={() => setViewing(null)}>Close</Button>}>
        {viewing && (
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div className="sm:col-span-2"><dt className="text-xs uppercase text-navy-500">Title</dt><dd className="mt-1 font-medium">{viewing.title}</dd></div>
            <div className="sm:col-span-2"><dt className="text-xs uppercase text-navy-500">Message</dt><dd className="mt-1 leading-relaxed">{viewing.message}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Customer</dt><dd className="mt-1">{viewing.customer}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Source</dt><dd className="mt-1">{viewing.source}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Theme</dt><dd className="mt-1">{viewing.displayTheme}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Sentiment</dt><dd className="mt-1"><Badge tone={viewing.sentiment}>{viewing.sentiment}</Badge></dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Votes</dt><dd className="mt-1">{viewing.votes}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Date</dt><dd className="mt-1">{formatDate(viewing.createdAt)}</dd></div>
          </dl>
        )}
      </Modal>

      {/* Edit modal */}
      {editing && <FeedbackEditModal record={editing} themes={themeNames} busy={busy} onClose={() => setEditing(null)} onSave={saveEdit} />}

      {/* Delete confirm */}
      <Modal
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title="Confirm deletion"
        footer={<>
          <Button variant="outline" onClick={() => setConfirm(null)}>Cancel</Button>
          <Button variant="danger" loading={busy} onClick={runDelete}>Delete</Button>
        </>}
      >
        <div className="flex gap-3 text-sm">
          <AlertTriangle size={20} className="shrink-0 text-rose-600" />
          <p>Delete <strong>{confirm?.label}</strong>? This cannot be undone.</p>
        </div>
      </Modal>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <div className="min-w-[150px]">
      <label className="mb-1.5 block text-xs font-medium text-navy-500">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input py-2" aria-label={`Filter by ${label}`}>
        <option value="">All</option>
        {options.map((o) => <option key={o} value={o} className="capitalize">{o}</option>)}
      </select>
    </div>
  );
}

function FeedbackEditModal({ record, themes, busy, onClose, onSave }) {
  const [form, setForm] = useState({ title: record.title, message: record.message, customer: record.customer, sentiment: record.sentiment, theme: record.theme, votes: record.votes });
  const [err, setErr] = useState('');
  const submit = (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.message.trim()) return setErr('Title and message are required.');
    if (Number(form.votes) < 0 || Number.isNaN(Number(form.votes))) return setErr('Votes must be a non-negative number.');
    setErr('');
    onSave({ ...form, votes: Number(form.votes) });
  };
  return (
    <Modal open onClose={onClose} title="Edit feedback" wide footer={<>
      <Button variant="outline" onClick={onClose}>Cancel</Button>
      <Button type="submit" form="edit-feedback" loading={busy}>Save changes</Button>
    </>}>
      <form id="edit-feedback" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Input label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="sm:col-span-2" />
        <div className="sm:col-span-2">
          <label className="mb-1.5 block text-sm font-medium" htmlFor="fb-message">Message</label>
          <textarea id="fb-message" rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="input" />
        </div>
        <Input label="Customer" value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })} />
        <Input label="Votes" type="number" min="0" value={form.votes} onChange={(e) => setForm({ ...form, votes: e.target.value })} />
        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="fb-sent">Sentiment</label>
          <select id="fb-sent" value={form.sentiment} onChange={(e) => setForm({ ...form, sentiment: e.target.value })} className="input">
            {SENTIMENTS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="fb-theme">Theme</label>
          <select id="fb-theme" value={form.theme} onChange={(e) => setForm({ ...form, theme: e.target.value })} className="input">
            {[...themes, 'Uncategorized'].map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        {err && <p role="alert" className="text-sm text-rose-600 sm:col-span-2">{err}</p>}
      </form>
    </Modal>
  );
}
