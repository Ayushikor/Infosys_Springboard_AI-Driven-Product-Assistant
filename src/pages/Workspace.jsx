import { useState } from 'react';
import { Plus, Pencil, Check, Briefcase, Activity, Upload } from 'lucide-react';
import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';
import { timeAgo, formatDate } from '../utils/formatters';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

export default function Workspace() {
  const { raw, derived, loading, error, refresh } = useAppData();
  const [editing, setEditing] = useState(null); // { mode, ws? }
  const [toast, setToast] = useState(null);

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load workspace" description={error} />;
  if (!raw || !derived) return null;

  const active = raw.workspaces.find((w) => w.id === raw.activeWorkspaceId) || raw.workspaces[0];

  const switchTo = async (id) => {
    const res = await apiClient.workspaces.switchTo(id);
    await refresh();
    setToast({ type: res.success ? 'success' : 'error', text: res.success ? 'Workspace switched.' : res.message });
  };

  const save = async (form) => {
    const res = editing.mode === 'create'
      ? await apiClient.workspaces.create(form)
      : await apiClient.workspaces.update(editing.ws.id, form);
    if (res.success) { setEditing(null); await refresh(); setToast({ type: 'success', text: editing.mode === 'create' ? 'Workspace created.' : 'Workspace updated.' }); }
    else setToast({ type: 'error', text: res.message });
    return res;
  };

  const stats = [
    { label: 'Total feedback', value: derived.feedbackCount },
    { label: 'Themes', value: derived.activeThemes },
    { label: 'Prioritized features', value: derived.prioritizedCount },
    { label: 'PRDs', value: derived.prdCount },
  ];

  return (
    <div className="space-y-6">
      {toast && (
        <div role="status" className={`flex items-center justify-between rounded-lg border p-3 text-sm ${toast.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
          {toast.text}<button onClick={() => setToast(null)} className="text-xs underline">Dismiss</button>
        </div>
      )}

      <div className="card flex flex-wrap items-start justify-between gap-4 p-6">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-indigo-50 text-accent dark:bg-indigo-500/15"><Briefcase size={22} /></div>
          <div>
            <h2 className="text-lg font-semibold">{active.name}</h2>
            <p className="mt-1 max-w-xl text-sm text-navy-500">{active.description || 'No description yet.'}</p>
            <p className="mt-2 text-xs text-navy-500">Created {formatDate(active.createdAt)}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setEditing({ mode: 'edit', ws: active })}><Pencil size={15} />Edit</Button>
          <Button onClick={() => setEditing({ mode: 'create' })}><Plus size={15} />New workspace</Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="card p-5">
            <p className="text-sm text-navy-500">{s.label}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h3 className="mb-4 text-sm font-semibold">Your workspaces</h3>
          <ul className="divide-y divide-slate-100 dark:divide-navy-700">
            {raw.workspaces.map((w) => (
              <li key={w.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{w.name} {w.id === active.id && <span className="ml-1 rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-accent-600 dark:bg-indigo-500/20 dark:text-indigo-300">ACTIVE</span>}</p>
                  <p className="truncate text-xs text-navy-500">{w.description || 'No description'}</p>
                </div>
                {w.id !== active.id && <Button variant="outline" className="!py-1.5 !text-xs" onClick={() => switchTo(w.id)}>Switch</Button>}
              </li>
            ))}
          </ul>
        </div>

        <div className="card p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold"><Activity size={15} />Workspace activity</div>
          {raw.activity.length === 0 ? <p className="text-sm text-navy-500">No activity yet.</p> : (
            <ul className="space-y-3">
              {raw.activity.slice(0, 8).map((a) => (
                <li key={a.id} className="text-sm">
                  <p className="text-navy-700 dark:text-slate-300">{a.text}</p>
                  <p className="text-xs text-navy-500">{timeAgo(a.at)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Recent uploads</h3>
          <a href="/feedback/upload" className="text-xs font-medium text-accent">Upload more →</a>
        </div>
        {raw.feedback.length === 0 ? (
          <EmptyState icon={Upload} title="No uploads yet" description="Imported feedback appears here." />
        ) : (
          <p className="text-sm text-navy-500">{raw.feedback.length} feedback record(s) in this workspace. See the Feedback List for the full table.</p>
        )}
      </div>

      {editing && <WorkspaceForm mode={editing.mode} ws={editing.ws} onClose={() => setEditing(null)} onSave={save} />}
    </div>
  );
}

function WorkspaceForm({ mode, ws, onClose, onSave }) {
  const [form, setForm] = useState({ name: ws?.name || '', description: ws?.description || '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.name.trim().length < 2) return setErr('Name must be at least 2 characters.');
    setBusy(true);
    const res = await onSave(form);
    setBusy(false);
    if (!res.success) setErr(res.message);
  };

  return (
    <Modal open onClose={onClose} title={mode === 'create' ? 'New workspace' : 'Edit workspace'} footer={<>
      <Button variant="outline" onClick={onClose}>Cancel</Button>
      <Button type="submit" form="ws-form" loading={busy}><Check size={15} />Save</Button>
    </>}>
      <form id="ws-form" onSubmit={submit} className="space-y-4">
        <Input label="Workspace name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <div>
          <label htmlFor="wsd" className="mb-1.5 block text-sm font-medium">Description</label>
          <textarea id="wsd" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input" />
        </div>
        {err && <p role="alert" className="text-sm text-rose-600">{err}</p>}
      </form>
    </Modal>
  );
}
