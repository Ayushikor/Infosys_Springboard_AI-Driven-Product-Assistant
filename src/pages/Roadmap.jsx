import { useMemo, useState } from 'react';
import { LayoutGrid, GanttChart, Plus, Flag, AlertTriangle, Pencil, Trash2 } from 'lucide-react';
import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';
import { formatDate } from '../utils/formatters';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const COLUMNS = ['Planned', 'In Progress', 'In Review', 'Completed'];
const PRIORITIES = ['High', 'Medium', 'Low'];
const DAY = 86400000;
const today = () => new Date().toISOString().slice(0, 10);
const toTime = (s) => new Date(s + 'T00:00:00').getTime();

export default function Roadmap() {
  const { raw, loading, error, refresh } = useAppData();
  const [view, setView] = useState('timeline');
  const [themeFilter, setThemeFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [editing, setEditing] = useState(null); // item | 'new'
  const [detail, setDetail] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null);
  const [toast, setToast] = useState(null);
  const [busy, setBusy] = useState(false);

  const items = useMemo(() => {
    if (!raw) return [];
    return raw.roadmap
      .filter((r) => !themeFilter || r.theme === themeFilter)
      .filter((r) => !priorityFilter || r.priority === priorityFilter);
  }, [raw, themeFilter, priorityFilter]);

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load roadmap" description={error} />;
  if (!raw) return null;

  const themes = [...new Set(raw.roadmap.map((r) => r.theme))];

  const move = async (id, status) => {
    const res = await apiClient.roadmap.update(id, { status });
    await refresh();
    if (!res.success) setToast({ type: 'error', text: res.message });
  };

  const save = async (form) => {
    setBusy(true);
    const res = editing === 'new' ? await apiClient.roadmap.create(form) : await apiClient.roadmap.update(editing.id, form);
    setBusy(false);
    if (res.success) { setEditing(null); await refresh(); setToast({ type: 'success', text: editing === 'new' ? 'Roadmap item added.' : 'Roadmap item updated.' }); }
    else setToast({ type: 'error', text: res.message });
  };

  const remove = async () => {
    setBusy(true);
    const res = await apiClient.roadmap.remove(confirmDel.id);
    setBusy(false);
    setConfirmDel(null);
    await refresh();
    setToast({ type: res.success ? 'success' : 'error', text: res.success ? 'Roadmap item deleted.' : res.message });
  };

  return (
    <div className="space-y-4">
      {toast && (
        <div role="status" className={`flex items-center justify-between rounded-lg border p-3 text-sm ${toast.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
          {toast.text}<button onClick={() => setToast(null)} className="text-xs underline">Dismiss</button>
        </div>
      )}

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="inline-flex rounded-lg bg-slate-100 p-1 dark:bg-navy-900" role="tablist" aria-label="Roadmap view">
          <button role="tab" aria-selected={view === 'timeline'} onClick={() => setView('timeline')} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ${view === 'timeline' ? 'bg-white shadow-sm dark:bg-navy-700' : 'text-navy-500'}`}><GanttChart size={15} />Timeline</button>
          <button role="tab" aria-selected={view === 'kanban'} onClick={() => setView('kanban')} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ${view === 'kanban' ? 'bg-white shadow-sm dark:bg-navy-700' : 'text-navy-500'}`}><LayoutGrid size={15} />Kanban</button>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="rt">Theme</label>
          <select id="rt" value={themeFilter} onChange={(e) => setThemeFilter(e.target.value)} className="input py-2"><option value="">All themes</option>{themes.map((t) => <option key={t}>{t}</option>)}</select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="rp">Priority</label>
          <select id="rp" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="input py-2"><option value="">All</option>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</select>
        </div>
        <div className="ml-auto"><Button onClick={() => setEditing('new')}><Plus size={16} />New item</Button></div>
      </div>

      {raw.roadmap.length === 0 ? (
        <EmptyState icon={Flag} title="No roadmap items" description="Add an item to start planning." action={<Button onClick={() => setEditing('new')}>New item</Button>} />
      ) : view === 'timeline' ? (
        <Timeline items={items} onOpen={setDetail} />
      ) : (
        <Kanban items={items} onMove={move} onOpen={setDetail} onEdit={setEditing} onDelete={setConfirmDel} />
      )}

      {/* Detail */}
      <Modal open={!!detail} onClose={() => setDetail(null)} title={detail?.name || ''} footer={<Button variant="outline" onClick={() => setDetail(null)}>Close</Button>}>
        {detail && (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-xs uppercase text-navy-500">Owner</dt><dd className="mt-0.5">{detail.owner}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Theme</dt><dd className="mt-0.5">{detail.theme}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Start</dt><dd className="mt-0.5">{formatDate(detail.startDate)}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Target</dt><dd className="mt-0.5">{formatDate(detail.targetDate)}</dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Priority</dt><dd className="mt-0.5"><Badge tone={detail.priority.toLowerCase()}>{detail.priority}</Badge></dd></div>
            <div><dt className="text-xs uppercase text-navy-500">Status</dt><dd className="mt-0.5">{detail.status}</dd></div>
          </dl>
        )}
      </Modal>

      {editing && <RoadmapForm item={editing === 'new' ? null : editing} themes={themes} busy={busy} onClose={() => setEditing(null)} onSave={save} />}

      <Modal open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Delete roadmap item" footer={<>
        <Button variant="outline" onClick={() => setConfirmDel(null)}>Cancel</Button>
        <Button variant="danger" loading={busy} onClick={remove}>Delete</Button>
      </>}>
        <div className="flex gap-3 text-sm"><AlertTriangle size={20} className="shrink-0 text-rose-600" /><p>Delete <strong>{confirmDel?.name}</strong> from the roadmap?</p></div>
      </Modal>
    </div>
  );
}

function Timeline({ items, onOpen }) {
  if (!items.length) return <EmptyState title="No items match your filters" />;

  const now = Date.now();
  // Span covers all dates, with a small margin on each side.
  const starts = items.map((i) => toTime(i.startDate));
  const ends = items.map((i) => toTime(i.targetDate));
  const min = Math.min(...starts, now) - 14 * DAY;
  const max = Math.max(...ends, now) + 14 * DAY;
  const span = max - min;
  const pct = (t) => ((t - min) / span) * 100;

  // Month ticks
  const ticks = [];
  const cursor = new Date(min);
  cursor.setDate(1); cursor.setHours(0, 0, 0, 0);
  while (cursor.getTime() < max) {
    ticks.push({ t: cursor.getTime(), label: cursor.toLocaleDateString(undefined, { month: 'short', year: '2-digit' }) });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  const sorted = [...items].sort((a, b) => toTime(a.startDate) - toTime(b.startDate));
  const todayPct = pct(now);
  const barTone = { High: 'bg-rose-500', Medium: 'bg-amber-500', Low: 'bg-slate-400' };

  return (
    <div className="card overflow-x-auto p-5">
      <div className="min-w-[760px]">
        {/* Axis */}
        <div className="relative ml-56 h-8 border-b border-slate-200 text-[11px] text-navy-500 dark:border-navy-700">
          {ticks.map((tk) => <span key={tk.t} className="absolute top-1" style={{ left: `${pct(tk.t)}%` }}>{tk.label}</span>)}
        </div>
        <div className="relative">
          {/* Today line */}
          {todayPct >= 0 && todayPct <= 100 && (
            <div className="absolute bottom-0 top-0 z-10 w-px bg-accent" style={{ left: `calc(14rem + (100% - 14rem) * ${todayPct / 100})` }} aria-label="Today">
              <span className="absolute -top-5 -translate-x-1/2 rounded bg-accent px-1 text-[10px] text-white">Today</span>
            </div>
          )}
          {sorted.map((item) => {
            const overdue = item.status !== 'Completed' && toTime(item.targetDate) < now;
            const left = pct(toTime(item.startDate));
            const width = Math.max(1.5, pct(toTime(item.targetDate)) - left);
            return (
              <div key={item.id} className="flex items-center border-b border-slate-100 py-2.5 last:border-0 dark:border-navy-700">
                <button onClick={() => onOpen(item)} className="w-56 shrink-0 pr-4 text-left">
                  <p className="truncate text-sm font-medium hover:text-accent">{item.name}</p>
                  <p className="truncate text-xs text-navy-500">{item.owner} · {item.status}</p>
                </button>
                <div className="relative h-7 flex-1">
                  <button
                    onClick={() => onOpen(item)}
                    className={`absolute top-0.5 h-6 rounded-md px-2 text-left text-[11px] font-medium text-white shadow-sm transition hover:brightness-110 ${item.status === 'Completed' ? 'bg-emerald-500' : barTone[item.priority] || 'bg-accent'} ${overdue ? 'ring-2 ring-rose-400 ring-offset-1 dark:ring-offset-navy-800' : ''}`}
                    style={{ left: `${left}%`, width: `${width}%`, minWidth: 80 }}
                    aria-label={`${item.name}: ${formatDate(item.startDate)} to ${formatDate(item.targetDate)}`}
                  >
                    <span className="block truncate">{item.priority}</span>
                  </button>
                </div>
                {overdue && <span className="ml-2 flex shrink-0 items-center gap-1 text-xs font-medium text-rose-600"><AlertTriangle size={13} />Overdue</span>}
              </div>
            );
          })}
        </div>
        <p className="mt-4 text-xs text-navy-500">Bars run from start to target date. Red outline marks overdue items. Milestones are target dates.</p>
      </div>
    </div>
  );
}

function Kanban({ items, onMove, onOpen, onEdit, onDelete }) {
  const [dragId, setDragId] = useState(null);
  const [overCol, setOverCol] = useState(null);

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {COLUMNS.map((col) => {
        const colItems = items.filter((i) => i.status === col);
        return (
          <div
            key={col}
            onDragOver={(e) => { e.preventDefault(); setOverCol(col); }}
            onDragLeave={() => setOverCol(null)}
            onDrop={(e) => { e.preventDefault(); if (dragId) onMove(dragId, col); setDragId(null); setOverCol(null); }}
            className={`flex min-h-[240px] flex-col rounded-xl border p-3 transition ${overCol === col ? 'border-accent bg-indigo-50/60 dark:bg-indigo-500/10' : 'border-slate-200 bg-slate-50/60 dark:border-navy-700 dark:bg-navy-900/40'}`}
            aria-label={`${col} column, ${colItems.length} items`}
          >
            <div className="mb-3 flex items-center justify-between px-1">
              <h3 className="text-sm font-semibold">{col}</h3>
              <span className="rounded-full bg-white px-2 text-xs tabular-nums text-navy-500 dark:bg-navy-700">{colItems.length}</span>
            </div>
            <div className="space-y-2">
              {colItems.map((item) => {
                const overdue = item.status !== 'Completed' && toTime(item.targetDate) < Date.now();
                return (
                  <div key={item.id} draggable onDragStart={() => setDragId(item.id)} onDragEnd={() => setDragId(null)} className={`card cursor-grab p-3 active:cursor-grabbing ${overdue ? 'ring-1 ring-rose-300' : ''}`}>
                    <div className="flex items-start justify-between gap-2">
                      <button onClick={() => onOpen(item)} className="text-left text-sm font-medium hover:text-accent">{item.name}</button>
                      <Badge tone={item.priority.toLowerCase()}>{item.priority}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-navy-500">{item.owner}</p>
                    <p className="mt-1 text-xs text-navy-500">{formatDate(item.startDate)} → {formatDate(item.targetDate)}</p>
                    {overdue && <p className="mt-1 flex items-center gap-1 text-xs text-rose-600"><AlertTriangle size={12} />Overdue</p>}
                    <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-2 dark:border-navy-700">
                      <label className="sr-only" htmlFor={`mv-${item.id}`}>Move {item.name}</label>
                      <select id={`mv-${item.id}`} value={item.status} onChange={(e) => onMove(item.id, e.target.value)} className="rounded-md border border-slate-300 bg-white px-1.5 py-1 text-xs dark:border-navy-700 dark:bg-navy-900">
                        {COLUMNS.map((c) => <option key={c}>{c}</option>)}
                      </select>
                      <div className="flex">
                        <button onClick={() => onEdit(item)} className="btn-ghost p-1" aria-label={`Edit ${item.name}`}><Pencil size={13} /></button>
                        <button onClick={() => onDelete(item)} className="btn-ghost p-1 hover:text-rose-600" aria-label={`Delete ${item.name}`}><Trash2 size={13} /></button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RoadmapForm({ item, themes, busy, onClose, onSave }) {
  const [form, setForm] = useState(() => item ? { ...item } : { name: '', owner: '', theme: themes[0] || '', priority: 'Medium', status: 'Planned', startDate: today(), targetDate: today() });
  const [err, setErr] = useState('');
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    if (!form.name.trim()) return setErr('Name is required.');
    if (!form.startDate || !form.targetDate) return setErr('Start and target dates are required.');
    if (form.targetDate < form.startDate) return setErr('Target date cannot be before start date.');
    setErr('');
    onSave(form);
  };

  return (
    <Modal open onClose={onClose} title={item ? 'Edit roadmap item' : 'New roadmap item'} footer={<>
      <Button variant="outline" onClick={onClose}>Cancel</Button>
      <Button type="submit" form="rm-form" loading={busy}>Save</Button>
    </>}>
      <form id="rm-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Input label="Name" value={form.name} onChange={set('name')} className="sm:col-span-2" />
        <Input label="Owner" value={form.owner} onChange={set('owner')} />
        <div><label className="mb-1.5 block text-sm font-medium" htmlFor="rf-theme">Theme</label><select id="rf-theme" value={form.theme} onChange={set('theme')} className="input">{themes.map((t) => <option key={t}>{t}</option>)}</select></div>
        <Input label="Start date" type="date" value={form.startDate} onChange={set('startDate')} />
        <Input label="Target date" type="date" value={form.targetDate} onChange={set('targetDate')} />
        <div><label className="mb-1.5 block text-sm font-medium" htmlFor="rf-pri">Priority</label><select id="rf-pri" value={form.priority} onChange={set('priority')} className="input">{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</select></div>
        <div><label className="mb-1.5 block text-sm font-medium" htmlFor="rf-st">Status</label><select id="rf-st" value={form.status} onChange={set('status')} className="input">{COLUMNS.map((c) => <option key={c}>{c}</option>)}</select></div>
        {err && <p role="alert" className="text-sm text-rose-600 sm:col-span-2">{err}</p>}
      </form>
    </Modal>
  );
}
