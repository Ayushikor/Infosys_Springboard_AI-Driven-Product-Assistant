import { Link } from 'react-router-dom';
import {
  TrendingUp,
  MessageSquareText,
  Tags,
  FileText,
  Map,
  BarChart3,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  AlertCircle,
  Target,
  Sparkles,
} from 'lucide-react';

import { useAppData } from '../context/AppDataContext';
import EmptyState from '../components/common/EmptyState';

function MetricCard({ label, value, description, icon: Icon }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium text-navy-500">{label}</p>
        <span className="rounded-lg bg-[#f0e2d8] p-2 text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
          <Icon size={16} />
        </span>
      </div>

      <p className="mt-3 text-2xl font-semibold text-[#211815] dark:text-white">
        {value}
      </p>

      <p className="mt-1 text-[10px] text-navy-500">{description}</p>
    </div>
  );
}

function InsightCard({ title, value, description, icon: Icon }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-black/[.07] p-3 dark:border-white/10">
      <span className="rounded-lg bg-[#f0e2d8] p-2 text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
        <Icon size={16} />
      </span>

      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-[#30231e] dark:text-white">
          {title}
        </p>

        <p className="mt-1 text-lg font-semibold text-[#80503d] dark:text-[#d9b8a5]">
          {value}
        </p>

        <p className="mt-1 text-[10px] text-navy-500">
          {description}
        </p>
      </div>
    </div>
  );
}

function ProgressBar({ label, value, total, color }) {
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-[11px] text-[#30231e] dark:text-white">
          {label}
        </span>

        <span className="text-[10px] font-semibold text-navy-500">
          {value} / {total}
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-[#eee5de] dark:bg-white/10">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${percentage}%`,
            background: color,
          }}
        />
      </div>

      <p className="mt-1 text-right text-[9px] text-navy-500">
        {percentage}% 
      </p>
    </div>
  );
}

export default function ExecutiveDashboard() {
  const { raw, derived, loading, error } = useAppData();

  if (loading) {
    return <div className="card h-64 animate-pulse" />;
  }

  if (error) {
    return (
      <EmptyState
        title="Could not load executive overview"
        description={error}
      />
    );
  }

  const feedback = raw?.feedback || [];
  const features = raw?.features || [];
  const roadmap = raw?.roadmap || [];
  const prds = raw?.prds || [];

  const sentiment = derived?.sentiment || {};

  const positive = Number(sentiment.positive || 0);
  const neutral = Number(sentiment.neutral || 0);
  const negative = Number(sentiment.negative || 0);

  const classified = positive + neutral + negative;

  const positiveRate = classified
    ? Math.round((positive / classified) * 100)
    : 0;

  const completedFeatures = features.filter((item) => {
    const status = String(item.status || '').toLowerCase();
    return status.includes('done') || status.includes('complete');
  }).length;

  const inProgressFeatures = features.filter((item) => {
    const status = String(item.status || '').toLowerCase();
    return status.includes('progress') || status.includes('development');
  }).length;

  const completedRoadmap = roadmap.filter((item) => {
    const status = String(item.status || '').toLowerCase();
    return status.includes('complete') || status.includes('done');
  }).length;

  const activeRoadmap = roadmap.filter((item) => {
    const status = String(item.status || '').toLowerCase();
    return status.includes('progress') || status.includes('active');
  }).length;

  const themeStats = (derived?.themeStats || [])
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  const totalThemeFeedback = themeStats.reduce(
    (sum, item) => sum + Number(item.count || 0),
    0
  );

  const topTheme = themeStats[0];

  const recentRoadmap = roadmap.slice(0, 5);

  return (
    <div className="space-y-5">
      {/* HEADER */}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2 text-[10px] text-navy-500">
            <span>Overview</span>
            <span>›</span>
            <strong className="text-[#80503d]">Executive</strong>
          </div>

          <h1 className="text-xl font-semibold tracking-tight text-[#211815] dark:text-white">
            Executive Overview
          </h1>

          <p className="mt-1 text-xs text-navy-500">
            Strategic visibility into customer signals, product health and delivery.
          </p>
        </div>

        <Link
          to="/strategy-report"
          className="btn-primary !px-3 !py-2 text-[11px]"
        >
          <BarChart3 size={14} />
          Strategy report
        </Link>
      </div>

      {/* HERO */}

      <section className="overflow-hidden rounded-2xl border border-[#d9c4b5] bg-gradient-to-r from-[#efe0d5] to-[#f8f1eb] p-5 dark:border-white/10 dark:from-[#30231e] dark:to-[#211815]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="text-[9px] font-bold uppercase tracking-[.18em] text-[#80503d] dark:text-[#d9b8a5]">
              Strategic intelligence
            </span>

            <h2 className="mt-2 text-lg font-semibold text-[#30231e] dark:text-white">
              Product performance at a glance.
            </h2>

            <p className="mt-1 max-w-xl text-[11px] leading-5 text-[#806b60] dark:text-[#c0aca1]">
              Monitor customer sentiment, understand product priorities
              and evaluate roadmap execution using your existing workspace data.
            </p>
          </div>

          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-white/60 text-[#80503d] dark:bg-white/10 dark:text-[#d9b8a5]">
            <TrendingUp size={30} strokeWidth={1.5} />
          </div>
        </div>
      </section>

      {/* KPI CARDS */}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Customer feedback"
          value={feedback.length}
          description="Total customer signals collected"
          icon={MessageSquareText}
        />

        <MetricCard
          label="Active themes"
          value={derived?.activeThemes || 0}
          description="Themes with customer evidence"
          icon={Tags}
        />

        <MetricCard
          label="Product features"
          value={features.length}
          description="Features in the product portfolio"
          icon={Target}
        />

        <MetricCard
          label="PRDs generated"
          value={prds.length}
          description="Product requirement documents"
          icon={FileText}
        />
      </div>

      {/* CUSTOMER HEALTH */}

      <section className="card p-4 sm:p-5">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-[#211815] dark:text-white">
            Customer sentiment overview
          </h2>

          <p className="mt-1 text-[10px] text-navy-500">
            Sentiment distribution from available feedback records.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col justify-center rounded-xl bg-[#f8f1eb] p-4 dark:bg-white/[.04]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-navy-500">
              Positive sentiment rate
            </p>

            <p className="mt-2 text-4xl font-semibold text-[#80503d] dark:text-[#d9b8a5]">
              {positiveRate}%
            </p>

            <p className="mt-1 text-[10px] text-navy-500">
              {classified} classified feedback records
            </p>
          </div>

          <div className="space-y-4">
            <ProgressBar
              label="Positive"
              value={positive}
              total={classified}
              color="#78917c"
            />

            <ProgressBar
              label="Neutral"
              value={neutral}
              total={classified}
              color="#c9a77f"
            />

            <ProgressBar
              label="Negative"
              value={negative}
              total={classified}
              color="#a85f4c"
            />
          </div>
        </div>
      </section>

      {/* BUSINESS INSIGHTS */}

      <div className="grid gap-3 xl:grid-cols-2">
        <section className="card p-4 sm:p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-[#211815] dark:text-white">
              Product portfolio health
            </h2>

            <p className="mt-1 text-[10px] text-navy-500">
              Feature delivery status based on recorded feature states.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <InsightCard
              title="Completed features"
              value={completedFeatures}
              description="Features marked complete"
              icon={CheckCircle2}
            />

            <InsightCard
              title="In progress"
              value={inProgressFeatures}
              description="Features under development"
              icon={Clock3}
            />
          </div>

          <div className="mt-4">
            <ProgressBar
              label="Feature completion"
              value={completedFeatures}
              total={features.length}
              color="#78917c"
            />
          </div>

          <div className="mt-4 flex justify-end">
            <Link
              to="/prioritization"
              className="text-[10px] font-semibold text-[#80503d] dark:text-[#d9b8a5]"
            >
              View product portfolio →
            </Link>
          </div>
        </section>

        <section className="card p-4 sm:p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-[#211815] dark:text-white">
              Roadmap execution
            </h2>

            <p className="mt-1 text-[10px] text-navy-500">
              Current state of recorded roadmap initiatives.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <InsightCard
              title="Completed milestones"
              value={completedRoadmap}
              description="Marked as completed"
              icon={CheckCircle2}
            />

            <InsightCard
              title="Active initiatives"
              value={activeRoadmap}
              description="Currently in progress"
              icon={Clock3}
            />
          </div>

          <div className="mt-4">
            <ProgressBar
              label="Roadmap completion"
              value={completedRoadmap}
              total={roadmap.length}
              color="#78917c"
            />
          </div>

          <div className="mt-4 flex justify-end">
            <Link
              to="/roadmap"
              className="text-[10px] font-semibold text-[#80503d] dark:text-[#d9b8a5]"
            >
              View roadmap →
            </Link>
          </div>
        </section>
      </div>

      {/* TOP CUSTOMER THEMES */}

      <section className="card p-4 sm:p-5">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-[#211815] dark:text-white">
            Leading customer themes
          </h2>

          <p className="mt-1 text-[10px] text-navy-500">
            Most frequently observed topics in customer feedback.
          </p>
        </div>

        {themeStats.length ? (
          <div className="space-y-4">
            {themeStats.map((theme, index) => {
              const percentage = totalThemeFeedback
                ? Math.round((theme.count / totalThemeFeedback) * 100)
                : 0;

              return (
                <div key={theme.name || index}>
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <span className="text-[11px] font-medium text-[#30231e] dark:text-white">
                      {theme.name}
                    </span>

                    <span className="text-[10px] text-navy-500">
                      {theme.count} records
                    </span>
                  </div>

                  <div className="h-2 overflow-hidden rounded-full bg-[#eee5de] dark:bg-white/10">
                    <div
                      className="h-full rounded-full bg-[#80503d] dark:bg-[#d9b8a5]"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="py-8 text-center text-xs text-navy-500">
            No customer themes available.
          </p>
        )}

        {topTheme && (
          <div className="mt-4 rounded-lg bg-[#f8f1eb] p-3 text-[10px] text-[#80503d] dark:bg-white/[.04] dark:text-[#d9b8a5]">
            <Sparkles size={13} className="mr-2 inline" />
            Leading observed theme: <strong>{topTheme.name}</strong>
          </div>
        )}
      </section>

      {/* ROADMAP SNAPSHOT */}

      <section className="card p-4 sm:p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[#211815] dark:text-white">
              Roadmap snapshot
            </h2>

            <p className="mt-1 text-[10px] text-navy-500">
              Recent product initiatives.
            </p>
          </div>

          <Link
            to="/roadmap"
            className="text-[10px] font-semibold text-[#80503d] dark:text-[#d9b8a5]"
          >
            Full roadmap →
          </Link>
        </div>

        {recentRoadmap.length ? (
          <div className="space-y-3">
            {recentRoadmap.map((item, index) => (
              <div
                key={item.id || index}
                className="flex items-center gap-3 border-b border-black/[.05] pb-3 last:border-0 last:pb-0 dark:border-white/[.06]"
              >
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#f0e2d8] text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
                  <Map size={16} />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-[#30231e] dark:text-white">
                    {item.name || item.title || `Initiative ${index + 1}`}
                  </p>

                  <p className="mt-1 text-[10px] text-navy-500">
                    {item.targetDate || item.target_date || 'Target date not specified'}
                  </p>
                </div>

                <span className="rounded-full bg-[#f0e2d8] px-2.5 py-1 text-[9px] font-semibold text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
                  {item.status || 'Planned'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="py-8 text-center text-xs text-navy-500">
            No roadmap initiatives available.
          </p>
        )}
      </section>

      {/* REPORT CTA */}

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#d9c4b5] bg-[#f3e8df] px-4 py-4 text-[#634638] dark:border-white/10 dark:bg-white/[.04] dark:text-[#d9b8a5]">
        <div className="flex items-center gap-2">
          <BarChart3 size={17} />

          <div>
            <p className="text-xs font-semibold">
              Strategic product intelligence
            </p>

            <p className="mt-1 text-[10px]">
              Review the complete strategy report.
            </p>
          </div>
        </div>

        <Link
          to="/strategy-report"
          className="inline-flex items-center gap-1 text-[10px] font-semibold underline underline-offset-4"
        >
          Open report
          <ArrowUpRight size={12} />
        </Link>
      </section>
    </div>
  );
}