import { Link } from 'react-router-dom';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import { MessageSquareText, Tags, ListOrdered, FileText, Upload, Sparkles, ListChecks, FilePlus2 } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useTheme } from '../context/ThemeContext';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import { formatDate, timeAgo } from '../utils/formatters';

const SENTIMENT_COLORS = { positive: '#10b981', neutral: '#94a3b8', negative: '#f43f5e' };

// Feedback per day for the last 14 days, derived from the current feedback records.
const buildTrend = (feedback) => {
  const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - (13 - i));
    return { key: d.toDateString(), label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), count: 0 };
  });
  feedback.forEach((f) => {
    const k = new Date(f.createdAt).toDateString();
    const hit = days.find((d) => d.key === k);
    if (hit) hit.count += 1;
  });
  return days;
};

function StatCard({ label, value, icon: Icon, to, tone }) {
  return (
    <Link to={to} className="card group p-5 transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-sm text-navy-500">{label}</p>
        <div className={`rounded-lg p-2 ${tone}`}><Icon size={16} /></div>
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums">{value}</p>
    </Link>
  );
}

export default function Dashboard() {
  const { raw, derived, loading, error } = useAppData();
  const { isDark } = useTheme();

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load dashboard" description={error} />;
  if (!raw || !derived) return null;

  const trend = buildTrend(raw.feedback);
  const sentimentData = Object.entries(derived.sentiment).map(([k, v]) => ({ name: k, value: v }));
  const totalSent = sentimentData.reduce((s, x) => s + x.value, 0);
  const topThemes = derived.themeStats.slice(0, 5);
  const highPriority = derived.prioritized.filter((f) => f.priority === 'High').slice(0, 5);
  const recent = [...raw.feedback].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)).slice(0, 5);
  const gridColor = isDark ? '#2a3558' : '#e2e8f0';
  const tickColor = isDark ? '#b8c0d4' : '#64708f';

  const negShare = totalSent ? Math.round((derived.sentiment.negative / totalSent) * 100) : 0;
  const topTheme = topThemes[0];
  const insight = topTheme && topTheme.count > 0
    ? `${topTheme.name} is the largest theme with ${topTheme.count} records (${topTheme.negativeShare}% negative). ${negShare}% of all feedback is negative overall.`
    : 'Upload feedback to generate insights.';

  return (
    <div className="space-y-6">
      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <Link to="/feedback/upload" className="btn-outline"><Upload size={16} />Upload Feedback</Link>
        <Link to="/themes" className="btn-outline"><Tags size={16} />Analyze Themes</Link>
        <Link to="/prioritization" className="btn-outline"><ListOrdered size={16} />Prioritize Features</Link>
        <Link to="/prd" className="btn-outline"><FilePlus2 size={16} />Generate PRD</Link>
      </div>

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Feedback" value={derived.feedbackCount} icon={MessageSquareText} to="/feedback" tone="bg-indigo-50 text-accent dark:bg-indigo-500/15" />
        <StatCard label="Active Themes" value={derived.activeThemes} icon={Tags} to="/themes" tone="bg-violet-50 text-violet-600 dark:bg-violet-500/15" />
        <StatCard label="Prioritized Features" value={derived.prioritizedCount} icon={ListOrdered} to="/prioritization" tone="bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15" />
        <StatCard label="Generated PRDs" value={derived.prdCount} icon={FileText} to="/prd" tone="bg-amber-50 text-amber-600 dark:bg-amber-500/15" />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        {/* Trend */}
        <div className="card p-5 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Feedback trend (14 days)</h2>
          </div>
          <div className="h-56">
            {raw.feedback.length === 0 ? <EmptyState title="No feedback yet" description="Upload a CSV or JSON file to see trends." /> : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend}>
                  <CartesianGrid stroke={gridColor} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: tickColor, fontSize: 11 }} tickLine={false} axisLine={false} interval={2} />
                  <YAxis allowDecimals={false} tick={{ fill: tickColor, fontSize: 11 }} tickLine={false} axisLine={false} width={28} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Sentiment */}
        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold">Sentiment distribution</h2>
          {totalSent === 0 ? <EmptyState title="No sentiment data" /> : (
            <div className="flex items-center gap-4">
              <div className="h-40 w-40 shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={sentimentData} dataKey="value" innerRadius={45} outerRadius={70} paddingAngle={3} stroke="none">
                      {sentimentData.map((s) => <Cell key={s.name} fill={SENTIMENT_COLORS[s.name]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="space-y-2 text-sm">
                {sentimentData.map((s) => (
                  <li key={s.name} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: SENTIMENT_COLORS[s.name] }} />
                    <span className="capitalize text-navy-500">{s.name}</span>
                    <span className="ml-auto font-medium tabular-nums">{s.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        {/* Top themes */}
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Top product themes</h2>
            <Link to="/themes" className="text-xs font-medium text-accent">View all</Link>
          </div>
          <ul className="space-y-3">
            {topThemes.map((t) => (
              <li key={t.id}>
                <div className="mb-1 flex justify-between text-sm"><span className="truncate">{t.name}</span><span className="tabular-nums text-navy-500">{t.count}</span></div>
                <div className="h-1.5 rounded-full bg-slate-100 dark:bg-navy-700"><div className="h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500" style={{ width: `${t.priorityScore}%` }} /></div>
              </li>
            ))}
          </ul>
        </div>

        {/* AI insight (mock/local) */}
        <div className="card p-5">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Sparkles size={16} className="text-accent" />Insight</div>
          <p className="text-sm leading-relaxed text-navy-700 dark:text-slate-300">{insight}</p>
          <p className="mt-3 text-xs text-navy-500">Generated by local rules. No external AI service.</p>
          <Link to="/chat" className="mt-4 inline-block text-xs font-medium text-accent">Ask the copilot →</Link>
        </div>

        {/* High priority */}
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">High-priority features</h2>
            <Link to="/prioritization" className="text-xs font-medium text-accent">View all</Link>
          </div>
          {highPriority.length === 0 ? <p className="text-sm text-navy-500">No high-priority features yet.</p> : (
            <ul className="divide-y divide-slate-100 dark:divide-navy-700">
              {highPriority.map((f) => (
                <li key={f.id} className="flex items-center justify-between py-2.5 text-sm">
                  <span className="truncate pr-2">{f.name}</span>
                  <span className="tabular-nums text-navy-500">RICE {f.rice}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        {/* Recent feedback */}
        <div className="card overflow-hidden xl:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-navy-700">
            <h2 className="text-sm font-semibold">Recent feedback</h2>
            <Link to="/feedback" className="text-xs font-medium text-accent">View all</Link>
          </div>
          {recent.length === 0 ? <EmptyState icon={ListChecks} title="No feedback yet" description="Import a CSV or JSON file to get started." action={<Link to="/feedback/upload" className="btn-primary">Upload feedback</Link>} /> : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-navy-500 dark:bg-navy-900/40">
                  <tr><th className="px-5 py-2.5">Title</th><th className="px-5 py-2.5">Customer</th><th className="px-5 py-2.5">Sentiment</th><th className="px-5 py-2.5">Date</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-navy-700">
                  {recent.map((f) => (
                    <tr key={f.id} className="hover:bg-slate-50 dark:hover:bg-navy-700/50">
                      <td className="max-w-[260px] truncate px-5 py-3 font-medium">{f.title}</td>
                      <td className="px-5 py-3 text-navy-500">{f.customer}</td>
                      <td className="px-5 py-3"><Badge tone={f.sentiment}>{f.sentiment}</Badge></td>
                      <td className="whitespace-nowrap px-5 py-3 text-navy-500">{formatDate(f.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent activity */}
        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold">Recent activity</h2>
          {raw.activity.length === 0 ? <p className="text-sm text-navy-500">No activity yet.</p> : (
            <ul className="space-y-4">
              {raw.activity.slice(0, 6).map((a) => (
                <li key={a.id} className="flex gap-3 text-sm">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
                  <div className="min-w-0">
                    <p className="text-navy-700 dark:text-slate-300">{a.text}</p>
                    <p className="text-xs text-navy-500">{timeAgo(a.at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
