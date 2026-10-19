import { useMemo, useState } from 'react';
import { Plus, Search, Download, Printer, Save, Pencil, FileText, Wand2 } from 'lucide-react';
import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';
import { generatePrdContent, contentToMarkdown, contentToText, SECTION_KEYS, SECTION_TITLES } from '../utils/prdGenerator';
import { formatDate } from '../utils/formatters';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const PRD_STATUSES = ['Draft', 'In Review', 'Approved', 'Archived'];
const STATUS_TONE = { Draft: 'neutral', 'In Review': 'accent', Approved: 'low', Archived: 'neutral' };

export default function PRDViewer() {
  const { raw, loading, error, refresh } = useAppData();
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState(null);

  const prds = useMemo(() => {
    if (!raw) return [];
    const q = search.trim().toLowerCase();
    return raw.prds.filter((p) => {
      const feat = raw.features.find((f) => f.id === p.featureId);
      return !q || p.title.toLowerCase().includes(q) || (feat?.name || '').toLowerCase().includes(q);
    });
  }, [raw, search]);

  const selected = raw?.prds.find((p) => p.id === selectedId) || prds[0] || null;

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load PRDs" description={error} />;
  if (!raw) return null;

  const featureFor = (id) => raw.features.find((f) => f.id === id);
  const unlinkedFeatures = raw.features.filter((f) => !raw.prds.some((p) => p.featureId === f.id));

  const onSave = async (patch) => {
    const res = await apiClient.prds.update(selected.id, patch);
    if (res.success) { await refresh(); setToast({ type: 'success', text: 'PRD saved.' }); }
    else setToast({ type: 'error', text: res.message });
  };

  return (
    <div className="space-y-4">
      {toast && (
        <div role="status" className={`flex items-center justify-between rounded-lg border p-3 text-sm ${toast.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
          {toast.text}<button onClick={() => setToast(null)} className="text-xs underline">Dismiss</button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        {/* List */}
        <div className="card flex flex-col overflow-hidden">
          <div className="space-y-3 border-b border-slate-200 p-4 dark:border-navy-700">
            <div className="relative">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-navy-500" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search documents" className="input pl-9" aria-label="Search PRDs" />
            </div>
            <Button className="w-full" onClick={() => setCreating(true)} disabled={unlinkedFeatures.length === 0}>
              <Plus size={16} />{unlinkedFeatures.length ? 'Create PRD from feature' : 'All features have PRDs'}
            </Button>
          </div>
          {prds.length === 0 ? (
            <EmptyState icon={FileText} title={raw.prds.length ? 'No matching PRDs' : 'No PRDs yet'} description="Create one from a prioritized feature." />
          ) : (
            <ul className="max-h-[70vh] divide-y divide-slate-100 overflow-y-auto dark:divide-navy-700">
              {prds.map((p) => {
                const f = featureFor(p.featureId);
                const active = selected?.id === p.id;
                return (
                  <li key={p.id}>
                    <button onClick={() => setSelectedId(p.id)} className={`w-full px-4 py-3 text-left transition ${active ? 'bg-indigo-50 dark:bg-indigo-500/10' : 'hover:bg-slate-50 dark:hover:bg-navy-700/50'}`} aria-current={active}>
                      <div className="flex items-start justify-between gap-2">
                        <p className="truncate text-sm font-medium">{p.title}</p>
                        <Badge tone={STATUS_TONE[p.status] || 'neutral'}>{p.status}</Badge>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-navy-500">{f?.name || 'Unlinked feature'}</p>
                      <p className="mt-1 text-[11px] text-navy-500">v{p.version} · Updated {formatDate(p.updatedAt)}</p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Viewer */}
        {selected ? (
          <PRDDocument key={selected.id} prd={selected} feature={featureFor(selected.featureId)} feedback={raw.feedback} themes={raw.themes} onSave={onSave} />
        ) : (
          <div className="card"><EmptyState icon={FileText} title="Select a PRD" description="Choose a document on the left to read or edit it." /></div>
        )}
      </div>

      {creating && (
        <CreatePrdModal
          features={unlinkedFeatures}
          feedback={raw.feedback}
          themes={raw.themes}
          onClose={() => setCreating(false)}
          onCreated={async (prd) => { setCreating(false); await refresh(); setSelectedId(prd.id); setToast({ type: 'success', text: 'PRD generated from template. You can edit it below.' }); }}
        />
      )}
    </div>
  );
}

function PRDDocument({ prd, feature, feedback, themes, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(prd.content || {});
  const [status, setStatus] = useState(prd.status);

  const content = prd.content || generatePrdContent({ feature: feature || { name: prd.title, theme: 'General' }, feedbackForTheme: feedback.filter((f) => f.theme === feature?.theme), rice: null });
  const exportName = prd.title.replace(/[^a-z0-9]+/gi, '-').toLowerCase();

  const download = (text, ext, mime) => {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${exportName}.${ext}`; a.click();
    URL.revokeObjectURL(url);
  };

  const save = async () => {
    await onSave({ content: draft, status });
    setEditing(false);
  };

  const changeStatus = async (s) => {
    setStatus(s);
    await onSave({ status: s });
  };

  return (
    <div className="card overflow-hidden print:shadow-none">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 p-5 dark:border-navy-700 print:hidden">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold">{prd.title}</h2>
          <p className="text-xs text-navy-500">Feature: {feature?.name || '—'} · Version {prd.version} · Created {formatDate(prd.createdAt)} · Updated {formatDate(prd.updatedAt)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={status} onChange={(e) => changeStatus(e.target.value)} className="input w-auto py-1.5 text-xs" aria-label="Document status">
            {PRD_STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
          {editing ? (
            <Button onClick={save}><Save size={15} />Save changes</Button>
          ) : (
            <Button variant="outline" onClick={() => { setDraft(content); setEditing(true); }}><Pencil size={15} />Edit</Button>
          )}
          <Button variant="outline" onClick={() => download(contentToMarkdown(prd.title, content), 'md', 'text/markdown')}><Download size={15} />.md</Button>
          <Button variant="outline" onClick={() => download(contentToText(prd.title, content), 'txt', 'text/plain')}><Download size={15} />.txt</Button>
          <Button variant="outline" onClick={() => window.print()}><Printer size={15} />Print</Button>
        </div>
      </div>

      <article className="prose-doc mx-auto max-w-3xl space-y-8 p-6 sm:p-10">
        <h1 className="text-2xl font-semibold">{prd.title}</h1>
        {SECTION_KEYS.map((k) => (
          <section key={k}>
            <h2 className="mb-2 border-b border-slate-200 pb-1.5 text-base font-semibold dark:border-navy-700">{SECTION_TITLES[k]}</h2>
            {editing ? (
              <textarea
                aria-label={SECTION_TITLES[k]}
                rows={Math.max(4, (draft[k] || '').split('\n').length + 1)}
                value={draft[k] || ''}
                onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
                className="input font-mono text-xs leading-relaxed"
              />
            ) : (
              <div className="whitespace-pre-line text-sm leading-relaxed text-navy-700 dark:text-slate-300">{content[k]}</div>
            )}
          </section>
        ))}
      </article>
    </div>
  );
}

function CreatePrdModal({ features, feedback, themes, onClose, onCreated }) {
  const [featureId, setFeatureId] = useState(features[0]?.id || '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const create = async () => {
    const feature = features.find((f) => f.id === featureId);
    if (!feature) return setErr('Select a feature.');
    setBusy(true);
    const theme = themes.find((t) => t.name === feature.theme);
    const linked = feedback.filter((f) => f.theme === feature.theme);
    const content = generatePrdContent({ feature, feedbackForTheme: linked, rice: null });
    const res = await apiClient.prds.create({
      title: `PRD: ${feature.name}`,
      featureId: feature.id,
      version: '0.1',
      status: 'Draft',
      content,
      themeId: theme?.id || null,
    });
    setBusy(false);
    if (res.success) onCreated(res.data);
    else setErr(res.message);
  };

  return (
    <Modal open onClose={onClose} title="Create PRD from feature" footer={<>
      <Button variant="outline" onClick={onClose}>Cancel</Button>
      <Button onClick={create} loading={busy}><Wand2 size={15} />Generate PRD</Button>
    </>}>
      <p className="text-sm text-navy-500">Generates a draft from a local template using the feature's details and linked feedback. No AI model is called.</p>
      <label htmlFor="feat" className="mt-4 block text-sm font-medium">Feature</label>
      <select id="feat" value={featureId} onChange={(e) => setFeatureId(e.target.value)} className="input mt-1.5">
        {features.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
      </select>
      {err && <p role="alert" className="mt-3 text-sm text-rose-600">{err}</p>}
    </Modal>
  );
}
