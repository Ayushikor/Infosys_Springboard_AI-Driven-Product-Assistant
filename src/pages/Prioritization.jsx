import { useMemo, useState } from 'react';
import { Plus, Pencil, Trash2, Search, AlertTriangle } from 'lucide-react';
import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';
import { computeRice } from '../utils/riceScore';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const STATUSES = ['Backlog', 'Planned', 'In Progress', 'In Review', 'Completed'];
const EMPTY = { name: '', theme: '', reach: '', impact: 1, confidence: 0.8, effort: '', status: 'Backlog', description: '' };
const IMPACT_LABEL = { 3: 'Massive (3)', 2: 'High (2)', 1: 'Medium (1)', 0.5: 'Low (0.5)', 0.25: 'Minimal (0.25)' };

export default function Prioritization() {
  const { raw, derived, loading, error, refresh } = useAppData();
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [sortDir, setSortDir] = useState('desc');
  const [modal, setModal] = useState(null); // { mode: 'create' | 'edit', feature? }
  const [confirmDel, setConfirmDel] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  const rows = useMemo(() => {
    if (!derived) return [];
    const q = search.trim().toLowerCase();
    return derived.prioritized
      .filter((f) => !q || f.name.toLowerCase().includes(q) || f.theme.toLowerCase().includes(q))
      .filter((f) => !priorityFilter || f.priority === priorityFilter)
      .sort((a, b) => (sortDir === 'desc' ? b.rice - a.rice : a.rice - b.rice));
  }, [derived, search, priorityFilter, sortDir]);

  const onDelete = async () => {
    setBusy(true);
    const res = await apiClient.prioritization.remove(confirmDel.id);
    setBusy(false);
    setConfirmDel(null);
    await refresh();
    setToast({ type: res.success ? 'success' : 'error', text: res.success ? 'Feature deleted.' : res.message });
  };

  const onStatusChange = async (id, status) => {
    const res = await apiClient.prioritization.update(id, { status });
    await refresh();
    if (!res.success) setToast({ type: 'error', text: res.message });
  };

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load features" description={error} />;
  if (!raw) return null;

  const themeNames = raw.themes.map((t) => t.name);

  return (
    <div className="space-y-4">
      {toast && (
        <div role="status" className={`flex items-center justify-between rounded-lg border p-3 text-sm ${toast.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
          {toast.text}<button onClick={() => setToast(null)} className="text-xs underline">Dismiss</button>
        </div>
      )}

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-[34px] text-navy-500" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search features or themes" className="input pl-9" aria-label="Search features" />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="pf">Priority</label>
          <select id="pf" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="input py-2">
            <option value="">All</option><option>High</option><option>Medium</option><option>Low</option>
          </select>
        </div>
        <Button variant="outline" onClick={() => setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))}>RICE {sortDir === 'desc' ? '↓' : '↑'}</Button>
        <Button onClick={() => setModal({ mode: 'create' })}><Plus size={16} />Add feature</Button>
      </div>

      <div className="card overflow-hidden">
        {rows.length === 0 ? (
          <EmptyState title={raw.features.length ? 'No features match' : 'No features yet'} description={raw.features.length ? 'Adjust your filters.' : 'Add a feature to start scoring.'} action={!raw.features.length && <Button onClick={() => setModal({ mode: 'create' })}>Add feature</Button>} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-navy-500 dark:bg-navy-900/40">
                <tr>
                  {['Feature', 'Theme', 'Reach', 'Impact', 'Confidence', 'Effort', 'RICE Score', 'Priority', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-4 py-3 font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-navy-700">
                {rows.map((f) => (
                  <tr key={f.id} className={`transition hover:bg-slate-50 dark:hover:bg-navy-700/50 ${f.priority === 'High' ? 'bg-rose-50/40 dark:bg-rose-500/5' : ''}`}>
                    <td className="max-w-[220px] px-4 py-3">
                      <p className="truncate font-medium">{f.name}</p>
                      {f.description && <p className="truncate text-xs text-navy-500">{f.description}</p>}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-navy-500">{f.theme}</td>
                    <td className="px-4 py-3 tabular-nums">{f.reach.toLocaleString()}</td>
                    <td className="px-4 py-3 tabular-nums">{f.impact}</td>
                    <td className="px-4 py-3 tabular-nums">{Math.round(f.confidence * 100)}%</td>
                    <td className="px-4 py-3 tabular-nums">{f.effort}</td>
                    <td className="px-4 py-3 font-semibold tabular-nums">{f.riceError ? <span className="text-rose-600" title={f.riceError}>Invalid</span> : f.rice.toLocaleString()}</td>
                    <td className="px-4 py-3"><Badge tone={f.priority.toLowerCase()}>{f.priority}</Badge></td>
                    <td className="px-4 py-3">
                      <select value={f.status} onChange={(e) => onStatusChange(f.id, e.target.value)} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs dark:border-navy-700 dark:bg-navy-900" aria-label={`Status for ${f.name}`}>
                        {STATUSES.map((s) => <option key={s}>{s}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button className="btn-ghost p-1.5" onClick={() => setModal({ mode: 'edit', feature: f })} aria-label={`Edit ${f.name}`}><Pencil size={15} /></button>
                        <button className="btn-ghost p-1.5 hover:text-rose-600" onClick={() => setConfirmDel(f)} aria-label={`Delete ${f.name}`}><Trash2 size={15} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-navy-500">RICE = (Reach × Impact × Confidence) ÷ Effort. Priority buckets are based on rank: top third High, middle third Medium, rest Low.</p>

      {modal && <FeatureModal mode={modal.mode} feature={modal.feature} themes={themeNames} onClose={() => setModal(null)} onSaved={async (msg) => { setModal(null); await refresh(); setToast({ type: 'success', text: msg }); }} />}

      <Modal open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Delete feature" footer={<>
        <Button variant="outline" onClick={() => setConfirmDel(null)}>Cancel</Button>
        <Button variant="danger" loading={busy} onClick={onDelete}>Delete</Button>
      </>}>
        <div className="flex gap-3 text-sm"><AlertTriangle size={20} className="shrink-0 text-rose-600" /><p>Delete <strong>{confirmDel?.name}</strong>? Linked PRDs and roadmap items are kept.</p></div>
      </Modal>
    </div>
  );
}

function FeatureModal({ mode, feature, themes, onClose, onSaved }) {
  const [form, setForm] = useState(() => feature ? { ...feature } : { ...EMPTY, theme: themes[0] || '' });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [serverErr, setServerErr] = useState('');

  const set = (k) => (e) => { setForm((f) => ({ ...f, [k]: e.target.value })); setErrors((er) => ({ ...er, [k]: undefined })); };

  // Live RICE preview. Uses the same function as the table, so the preview always matches the saved score.
  const preview = computeRice({ reach: form.reach, impact: Number(form.impact), confidence: Number(form.confidence), effort: form.effort });

  const validate = () => {
    const e = {};
    if (!String(form.name).trim()) e.name = 'Name is required.';
    if (form.reach === '' || Number(form.reach) < 0) e.reach = 'Reach must be 0 or greater.';
    const c = Number(form.confidence);
    if (Number.isNaN(c) || c < 0 || c > 1) e.confidence = 'Confidence must be between 0 and 1.';
    if (form.effort === '' || Number(form.effort) <= 0) e.effort = 'Effort must be greater than 0 to avoid division by zero.';
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    const payload = { ...form, reach: Number(form.reach), impact: Number(form.impact), confidence: Number(form.confidence), effort: Number(form.effort) };
    const res = mode === 'edit' ? await apiClient.prioritization.update(feature.id, payload) : await apiClient.prioritization.create(payload);
    setBusy(false);
    if (res.success) onSaved(mode === 'edit' ? 'Feature updated. RICE recalculated.' : 'Feature added.');
    else setServerErr(res.message);
  };

  return (
    <Modal open onClose={onClose} title={mode === 'edit' ? 'Edit feature' : 'Add feature'} wide footer={<>
      <Button variant="outline" onClick={onClose}>Cancel</Button>
      <Button type="submit" form="feature-form" loading={busy}>{mode === 'edit' ? 'Save' : 'Add feature'}</Button>
    </>}>
      <form id="feature-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Input label="Feature name" value={form.name} onChange={set('name')} error={errors.name} className="sm:col-span-2" />
        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="theme">Theme</label>
          <select id="theme" value={form.theme} onChange={set('theme')} className="input">
            {themes.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="status">Status</label>
          <select id="status" value={form.status} onChange={set('status')} className="input">
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <Input label="Reach (users / quarter)" type="number" min="0" value={form.reach} onChange={set('reach')} error={errors.reach} />
        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="impact">Impact</label>
          <select id="impact" value={form.impact} onChange={set('impact')} className="input">
            {Object.entries(IMPACT_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <Input label="Confidence (0–1)" type="number" step="0.05" min="0" max="1" value={form.confidence} onChange={set('confidence')} error={errors.confidence} hint="e.g. 0.8 = 80% confident" />
        <Input label="Effort (person-weeks)" type="number" step="0.5" min="0.1" value={form.effort} onChange={set('effort')} error={errors.effort} />
        <div className="rounded-lg bg-indigo-50 p-3 text-sm dark:bg-indigo-500/10 sm:col-span-2">
          <span className="text-navy-500">RICE preview: </span>
          <span className="font-semibold">{preview.error ? preview.error : preview.score.toLocaleString()}</span>
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1.5 block text-sm font-medium" htmlFor="desc">Description</label>
          <textarea id="desc" rows={2} value={form.description} onChange={set('description')} className="input" />
        </div>
        {serverErr && <p role="alert" className="text-sm text-rose-600 sm:col-span-2">{serverErr}</p>}
      </form>
    </Modal>
  );
}
