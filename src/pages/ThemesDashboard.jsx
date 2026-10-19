import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Sparkles, TrendingUp, TrendingDown, Minus, X } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { apiClient } from '../api/apiClient';
import { analyzeThemes } from '../utils/themeAnalyzer';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';
import { formatDate } from '../utils/formatters';

// Trend compares the last 7 days to the 7 days before that.
const trendOf = (items) => {
  const now = Date.now(), week = 7 * 86400000;
  const recent = items.filter((f) => now - new Date(f.createdAt) < week).length;
  const prior = items.filter((f) => { const age = now - new Date(f.createdAt); return age >= week && age < 2 * week; }).length;
  if (recent > prior) return 'up';
  if (recent < prior) return 'down';
  return 'flat';
};

export default function ThemesDashboard() {
  const { raw, loading, error, refresh } = useAppData();
  const [search, setSearch] = useState('');
  const [minCount, setMinCount] = useState(0);
  const [sortBy, setSortBy] = useState('priority');
  const [active, setActive] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  const stats = useMemo(() => (raw ? analyzeThemes(raw.feedback, raw.themes) : []), [raw]);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return stats
      .filter((t) => !q || t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q))
      .filter((t) => t.count >= minCount)
      .sort((a, b) => {
        if (sortBy === 'count') return b.count - a.count;
        if (sortBy === 'negative') return b.negativeShare - a.negativeShare;
        if (sortBy === 'name') return a.name.localeCompare(b.name);
        return b.priorityScore - a.priorityScore;
      });
  }, [stats, search, minCount, sortBy]);

  // Re-runs the local analysis against current feedback and persists the run time.
  const onAnalyze = async () => {
    setAnalyzing(true);
    await refresh();
    setLastRun(new Date());
    setAnalyzing(false);
  };

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load themes" description={error} />;
  if (!raw) return null;

  const TrendIcon = { up: TrendingUp, down: TrendingDown, flat: Minus };
  const trendTone = { up: 'text-rose-600', down: 'text-emerald-600', flat: 'text-navy-500' };

  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold"><Sparkles size={16} className="text-accent" />Mock / local theme analysis</div>
          <p className="mt-1 text-xs text-navy-500">Keyword matching runs in your browser. No external AI service is used. {lastRun && `Last run ${lastRun.toLocaleTimeString()}.`}</p>
        </div>
        <Button onClick={onAnalyze} loading={analyzing}>Analyze Themes</Button>
      </div>

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-[34px] text-navy-500" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search themes" className="input pl-9" aria-label="Search themes" />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="min">Min. feedback</label>
          <select id="min" value={minCount} onChange={(e) => setMinCount(Number(e.target.value))} className="input py-2">
            <option value={0}>Any</option><option value={1}>1+</option><option value={3}>3+</option><option value={5}>5+</option>
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="sort">Sort by</label>
          <select id="sort" value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="input py-2">
            <option value="priority">Priority score</option><option value="count">Feedback count</option><option value="negative">Negative share</option><option value="name">Name</option>
          </select>
        </div>
      </div>

      {raw.feedback.length === 0 ? (
        <EmptyState title="No feedback to analyze" description="Upload feedback first, then run the analysis." action={<Link to="/feedback/upload" className="btn-primary">Upload feedback</Link>} />
      ) : visible.length === 0 ? (
        <EmptyState title="No themes match your filters" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((t) => {
            const Trend = TrendIcon[trendOf(t.items)];
            const tone = trendTone[trendOf(t.items)];
            const impact = t.count === 0 ? 'None' : t.priorityScore >= 66 ? 'High' : t.priorityScore >= 33 ? 'Medium' : 'Low';
            const total = t.count || 1;
            return (
              <button key={t.id} onClick={() => setActive(t)} className="card group flex flex-col p-5 text-left transition hover:-translate-y-0.5 hover:shadow-md">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold group-hover:text-accent">{t.name}</h3>
                  <span className={`flex items-center gap-1 text-xs font-medium ${tone}`}><Trend size={14} />{trendOf(t.items)}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-navy-500">{t.description}</p>

                <div className="mt-4 flex items-baseline justify-between">
                  <span className="text-2xl font-semibold tabular-nums">{t.count}</span>
                  <span className="text-xs text-navy-500">feedback items</span>
                </div>

                <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-navy-700" aria-label="Sentiment distribution">
                  <div className="bg-emerald-500" style={{ width: `${(t.positive / total) * 100}%` }} />
                  <div className="bg-slate-400" style={{ width: `${(t.neutral / total) * 100}%` }} />
                  <div className="bg-rose-500" style={{ width: `${(t.negative / total) * 100}%` }} />
                </div>
                <div className="mt-1.5 flex justify-between text-[11px] text-navy-500">
                  <span>{t.positive} positive</span><span>{t.neutral} neutral</span><span>{t.negative} negative</span>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-100 pt-3 text-xs dark:border-navy-700">
                  <div><p className="text-navy-500">Customer impact</p><p className="mt-0.5 font-medium">{t.totalVotes} votes</p></div>
                  <div><p className="text-navy-500">Priority score</p><p className="mt-0.5 flex items-center gap-2 font-medium">{t.priorityScore}<Badge tone={impact.toLowerCase()}>{impact}</Badge></p></div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <ThemeDetailModal theme={active} onClose={() => setActive(null)} onSaveKeywords={async (kw) => {
        const res = await apiClient.themes.saveKeywords(active.id, kw);
        if (res.success) { await refresh(); }
        return res;
      }} />
    </div>
  );
}

function ThemeDetailModal({ theme, onClose, onSaveKeywords }) {
  const [kwText, setKwText] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  if (!theme) return null;
  const draft = kwText ?? theme.keywords.join(', ');

  const save = async () => {
    setSaving(true);
    const keywords = draft.split(',').map((k) => k.trim().toLowerCase()).filter(Boolean);
    const res = await onSaveKeywords(keywords);
    setSaving(false);
    setMsg(res.success ? 'Keywords saved. Analysis updated.' : res.message);
  };

  return (
    <Modal open onClose={() => { setKwText(null); setMsg(''); onClose(); }} title={theme.name} wide footer={<Button variant="outline" onClick={onClose}>Close</Button>}>
      <p className="text-sm text-navy-500">{theme.description}</p>
      <div className="mt-4 grid grid-cols-3 gap-3 text-center text-sm">
        <div className="rounded-lg bg-slate-50 p-3 dark:bg-navy-900/40"><p className="text-xl font-semibold">{theme.count}</p><p className="text-xs text-navy-500">Items</p></div>
        <div className="rounded-lg bg-slate-50 p-3 dark:bg-navy-900/40"><p className="text-xl font-semibold">{theme.totalVotes}</p><p className="text-xs text-navy-500">Votes</p></div>
        <div className="rounded-lg bg-slate-50 p-3 dark:bg-navy-900/40"><p className="text-xl font-semibold">{theme.priorityScore}</p><p className="text-xs text-navy-500">Priority</p></div>
      </div>

      <h3 className="mt-6 text-sm font-semibold">Related feedback</h3>
      {theme.items.length === 0 ? <p className="mt-2 text-sm text-navy-500">No feedback currently maps to this theme.</p> : (
        <ul className="mt-2 max-h-60 divide-y divide-slate-100 overflow-y-auto dark:divide-navy-700">
          {theme.items.map((f) => (
            <li key={f.id} className="py-2.5 text-sm">
              <div className="flex items-center justify-between gap-2"><span className="font-medium">{f.title}</span><Badge tone={f.sentiment}>{f.sentiment}</Badge></div>
              <p className="text-xs text-navy-500">{f.customer} · {f.votes} votes · {formatDate(f.createdAt)}</p>
            </li>
          ))}
        </ul>
      )}

      <h3 className="mt-6 text-sm font-semibold">Matching keywords</h3>
      <p className="mt-1 text-xs text-navy-500">Comma-separated. Used when feedback has no explicit theme.</p>
      <textarea value={draft} onChange={(e) => setKwText(e.target.value)} rows={2} className="input mt-2" aria-label="Keywords" />
      <div className="mt-2 flex items-center gap-3">
        <Button variant="outline" onClick={save} loading={saving}>Save keywords</Button>
        {msg && <span className="text-xs text-navy-500">{msg}</span>}
      </div>
    </Modal>
  );
}
