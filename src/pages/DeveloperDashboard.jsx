
import { Link } from 'react-router-dom';
import {
  Code2,
  FileText,
  GitBranch,
  Layers3,
  MessageSquare,
  ArrowUpRight,
  Clock3,
  CheckCircle2,
  AlertCircle,
  Boxes,
  ClipboardList,
  Package,
  Activity,
  Terminal,
  CalendarDays,
} from 'lucide-react';

import { useAppData } from '../context/AppDataContext';
import EmptyState from '../components/common/EmptyState';

// --------------------------------------------------
// REUSABLE COMPONENTS
// --------------------------------------------------

function StatCard({ label, value, description, icon: Icon }) {
  return (
    <div className="card min-w-0 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium text-navy-500">
          {label}
        </p>

        <span className="rounded-lg bg-[#f0e2d8] p-2 text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
          <Icon size={16} />
        </span>
      </div>

      <p className="mt-3 text-2xl font-semibold text-[#211815] dark:text-white">
        {value}
      </p>

      <p className="mt-1 text-[10px] text-navy-500">
        {description}
      </p>
    </div>
  );
}

function QuickLink({ to, icon: Icon, title, description }) {
  return (
    <Link
      to={to}
      className="card group flex items-center gap-3 p-4 transition hover:-translate-y-0.5 hover:shadow-soft"
    >
      <span className="rounded-xl bg-[#f0e2d8] p-3 text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
        <Icon size={18} />
      </span>

      <span className="min-w-0 flex-1">
        <span className="block text-xs font-semibold text-[#30231e] dark:text-white">
          {title}
        </span>

        <span className="mt-1 block text-[10px] text-navy-500">
          {description}
        </span>
      </span>

      <ArrowUpRight
        size={15}
        className="text-navy-500 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
      />
    </Link>
  );
}

function StatusBadge({ status }) {
  const normalized = String(status || 'Backlog').toLowerCase();

  let styles =
    'bg-[#f0e2d8] text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]';

  if (
    normalized.includes('done') ||
    normalized.includes('complete')
  ) {
    styles =
      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
  } else if (
    normalized.includes('progress') ||
    normalized.includes('development')
  ) {
    styles =
      'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
  } else if (normalized.includes('blocked')) {
    styles =
      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
  }

  return (
    <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[9px] font-semibold ${styles}`}>
      {status || 'Backlog'}
    </span>
  );
}

function SectionHeading({ title, description, action, to }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-sm font-semibold text-[#211815] dark:text-white">
          {title}
        </h2>

        <p className="mt-1 text-[10px] text-navy-500">
          {description}
        </p>
      </div>

      {action && (
        <Link
          to={to}
          className="text-[10px] font-semibold text-[#80503d] dark:text-[#d9b8a5]"
        >
          {action} →
        </Link>
      )}
    </div>
  );
}

// --------------------------------------------------
// DEVELOPER DASHBOARD
// --------------------------------------------------

export default function DeveloperDashboard() {
  const { raw, loading, error } = useAppData();

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="card h-36 animate-pulse" />
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="card h-28 animate-pulse"
            />
          ))}
        </div>
        <div className="card h-64 animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Could not load developer workspace"
        description={error}
      />
    );
  }

  const features = Array.isArray(raw?.features)
    ? raw.features
    : [];

  const roadmap = Array.isArray(raw?.roadmap)
    ? raw.roadmap
    : [];

  const prds = Array.isArray(raw?.prds)
    ? raw.prds
    : [];

  const feedback = Array.isArray(raw?.feedback)
    ? raw.feedback
    : [];

  // Feature status calculations

  const getStatus = (item) =>
    String(item.status || 'Backlog').toLowerCase();

  const completed = features.filter((item) => {
    const status = getStatus(item);

    return (
      status.includes('done') ||
      status.includes('complete')
    );
  }).length;

  const inProgress = features.filter((item) => {
    const status = getStatus(item);

    return (
      status.includes('progress') ||
      status.includes('development')
    );
  }).length;

  const blocked = features.filter((item) =>
    getStatus(item).includes('blocked')
  ).length;

  const backlog = features.filter((item) => {
    const status = getStatus(item);

    return (
      status.includes('backlog') ||
      status.includes('planned')
    );
  }).length;

  const completionRate = features.length
    ? Math.round((completed / features.length) * 100)
    : 0;

  const completedRoadmap = roadmap.filter((item) => {
    const status = getStatus(item);

    return (
      status.includes('done') ||
      status.includes('complete')
    );
  }).length;

  const recentFeatures = features.slice(0, 6);
  const recentRoadmap = roadmap.slice(0, 5);
  const recentPRDs = prds.slice(0, 4);

  // ------------------------------------------------
  // RENDER
  // ------------------------------------------------

  return (
    <div className="space-y-5">

      {/* HEADER */}

      <div className="flex flex-wrap items-center justify-between gap-3">

        <div>
          <div className="mb-1 flex items-center gap-2 text-[10px] text-navy-500">
            <span>Workspace</span>
            <span>›</span>
            <strong className="text-[#80503d]">
              Developer
            </strong>
          </div>

          <h1 className="text-xl font-semibold tracking-tight text-[#211815] dark:text-white">
            Developer Workspace
          </h1>

          <p className="mt-1 text-xs text-navy-500">
            Your technical workspace for product development and delivery.
          </p>
        </div>

        <Link
          to="/workspace"
          className="btn-primary !px-3 !py-2 text-[11px]"
        >
          <Code2 size={14} />
          Open workspace
        </Link>

      </div>

      {/* HERO */}

      <section className="overflow-hidden rounded-2xl border border-[#d9c4b5] bg-gradient-to-r from-[#efe0d5] to-[#f8f1eb] p-5 dark:border-white/10 dark:from-[#30231e] dark:to-[#211815]">

        <div className="flex flex-wrap items-center justify-between gap-4">

          <div>
            <span className="text-[9px] font-bold uppercase tracking-[.18em] text-[#80503d] dark:text-[#d9b8a5]">
              DEVELOPER PORTAL
            </span>

            <h2 className="mt-2 text-lg font-semibold text-[#30231e] dark:text-white">
              From product vision to implementation.
            </h2>

            <p className="mt-1 max-w-lg text-[11px] leading-5 text-[#806b60] dark:text-[#c0aca1]">
              Access product requirements, understand feature
              specifications, review delivery milestones and
              collaborate with your product team.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">

              <Link
                to="/prd"
                className="inline-flex items-center gap-2 rounded-lg bg-[#80503d] px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-[#68402f]"
              >
                <FileText size={13} />
                View PRDs
              </Link>

              <Link
                to="/roadmap"
                className="inline-flex items-center gap-2 rounded-lg border border-[#80503d]/20 bg-white/50 px-3 py-2 text-[10px] font-semibold text-[#80503d] transition hover:bg-white/80 dark:border-white/20 dark:bg-white/10 dark:text-[#e6c9b8]"
              >
                <GitBranch size={13} />
                View roadmap
              </Link>

            </div>
          </div>

          <div className="grid h-20 w-20 shrink-0 place-items-center rounded-2xl bg-white/60 text-[#80503d] dark:bg-white/10 dark:text-[#d9b8a5]">
            <Code2 size={36} strokeWidth={1.4} />
          </div>

        </div>
      </section>

      {/* DEVELOPMENT STATISTICS */}

      <section>

        <SectionHeading
          title="Development overview"
          description="A snapshot of the product feature lifecycle."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

          <StatCard
            label="Total features"
            value={features.length}
            description="Features in the product workspace"
            icon={Layers3}
          />

          <StatCard
            label="In progress"
            value={inProgress}
            description="Features under development"
            icon={Activity}
          />

          <StatCard
            label="Completed"
            value={completed}
            description="Features marked as completed"
            icon={CheckCircle2}
          />

          <StatCard
            label="Blocked"
            value={blocked}
            description="Features requiring attention"
            icon={AlertCircle}
          />

        </div>
      </section>

      {/* QUICK ACCESS */}

      <section>

        <SectionHeading
          title="Development tools"
          description="Your essential product development resources."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">

          <QuickLink
            to="/workspace"
            icon={Boxes}
            title="Workspace"
            description="Explore your product workspace"
          />

          <QuickLink
            to="/prd"
            icon={FileText}
            title="Product requirements"
            description="Review PRDs and specifications"
          />

          <QuickLink
            to="/chat"
            icon={MessageSquare}
            title="AI Assistant"
            description="Get assistance with product-related queries"
          />

          <QuickLink
            to="/roadmap"
            icon={GitBranch}
            title="Product roadmap"
            description="Track upcoming product milestones"
          />

        </div>
      </section>

      {/* FEATURE DEVELOPMENT */}

      <section className="card p-4 sm:p-5">

        <SectionHeading
          title="Feature development tracker"
          description="Feature records and their current development status."
          action="View workspace"
          to="/workspace"
        />

        {/* PROGRESS SUMMARY */}

        <div className="mb-5 rounded-xl bg-[#f8f1eb] p-4 dark:bg-white/[.04]">

          <div className="mb-2 flex items-center justify-between gap-2">

            <div>
              <p className="text-[11px] font-semibold text-[#30231e] dark:text-white">
                Overall completion
              </p>

              <p className="mt-1 text-[10px] text-navy-500">
                Based on recorded feature statuses
              </p>
            </div>

            <span className="text-lg font-semibold text-[#80503d] dark:text-[#d9b8a5]">
              {completionRate}%
            </span>

          </div>

          <div className="h-2 overflow-hidden rounded-full bg-[#e8dcd2] dark:bg-white/10">
            <div
              className="h-full rounded-full bg-[#80503d] transition-all duration-500 dark:bg-[#d9b8a5]"
              style={{ width: `${completionRate}%` }}
            />
          </div>

          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">

            <span className="text-[9px] text-navy-500">
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-green-600" />
              Completed: {completed}
            </span>

            <span className="text-[9px] text-navy-500">
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-blue-500" />
              In progress: {inProgress}
            </span>

            <span className="text-[9px] text-navy-500">
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-500" />
              Backlog: {backlog}
            </span>

          </div>

        </div>

        {/* FEATURE TABLE */}

        {recentFeatures.length > 0 ? (

          <div className="overflow-x-auto">

            <table className="w-full min-w-[480px] text-left">

              <thead>
                <tr className="border-b border-black/10 text-[10px] text-navy-500 dark:border-white/10">

                  <th className="pb-3 font-medium">
                    Feature
                  </th>

                  <th className="pb-3 font-medium">
                    Theme
                  </th>

                  <th className="pb-3 font-medium">
                    Status
                  </th>

                </tr>
              </thead>

              <tbody>

                {recentFeatures.map((feature, index) => (

                  <tr
                    key={feature.id || index}
                    className="border-b border-black/[.05] last:border-0 dark:border-white/[.06]"
                  >

                    <td className="py-3 pr-3">

                      <p className="text-xs font-medium text-[#30231e] dark:text-white">
                        {feature.name || feature.title || `Feature ${index + 1}`}
                      </p>

                      {feature.description && (
                        <p className="mt-1 max-w-xs truncate text-[9px] text-navy-500">
                          {feature.description}
                        </p>
                      )}

                    </td>

                    <td className="py-3 pr-3 text-[10px] text-navy-500">
                      {feature.theme || 'Uncategorized'}
                    </td>

                    <td className="py-3">
                      <StatusBadge status={feature.status} />
                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        ) : (

          <div className="py-8 text-center">

            <Layers3
              size={25}
              className="mx-auto mb-2 text-navy-500"
            />

            <p className="text-xs font-medium text-[#30231e] dark:text-white">
              No feature records available
            </p>

            <p className="mt-1 text-[10px] text-navy-500">
              Feature information will appear here when available.
            </p>

          </div>

        )}

      </section>

      {/* PRD LIBRARY */}

      <section className="card p-4 sm:p-5">

        <SectionHeading
          title="Product requirements"
          description="Recently available product requirement documents."
          action="View all PRDs"
          to="/prd"
        />

        {recentPRDs.length > 0 ? (

          <div className="space-y-3">

            {recentPRDs.map((prd, index) => (

              <Link
                key={prd.id || index}
                to="/prd"
                className="flex items-center gap-3 rounded-xl border border-black/[.06] p-3 transition hover:bg-[#f8f1eb] dark:border-white/10 dark:hover:bg-white/[.04]"
              >

                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#f0e2d8] text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
                  <FileText size={17} />
                </div>

                <div className="min-w-0 flex-1">

                  <p className="truncate text-xs font-semibold text-[#30231e] dark:text-white">
                    {prd.title || prd.name || `Product document ${index + 1}`}
                  </p>

                  <p className="mt-1 text-[9px] text-navy-500">
                    {prd.version ? `Version ${prd.version}` : 'Product requirements'}
                  </p>

                </div>

                <StatusBadge status={prd.status || 'Available'} />

                <ArrowUpRight
                  size={14}
                  className="shrink-0 text-navy-500"
                />

              </Link>

            ))}

          </div>

        ) : (

          <div className="py-7 text-center">
            <FileText
              size={24}
              className="mx-auto mb-2 text-navy-500"
            />

            <p className="text-xs text-navy-500">
              No product requirement documents available.
            </p>
          </div>

        )}

      </section>

      {/* ROADMAP */}

      <section className="card p-4 sm:p-5">

        <SectionHeading
          title="Upcoming roadmap"
          description="Product delivery milestones and their current status."
          action="View roadmap"
          to="/roadmap"
        />

        {recentRoadmap.length > 0 ? (

          <div className="space-y-3">

            {recentRoadmap.map((item, index) => (

              <div
                key={item.id || index}
                className="flex items-center gap-3 border-b border-black/[.05] pb-3 last:border-0 last:pb-0 dark:border-white/[.06]"
              >

                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#f0e2d8] text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
                  <CalendarDays size={16} />
                </div>

                <div className="min-w-0 flex-1">

                  <p className="truncate text-xs font-semibold text-[#30231e] dark:text-white">
                    {item.name || item.title || `Roadmap item ${index + 1}`}
                  </p>

                  <p className="mt-1 text-[10px] text-navy-500">
                    {item.targetDate || item.target_date || 'Target date not specified'}
                  </p>

                </div>

                <StatusBadge status={item.status} />

              </div>

            ))}

          </div>

        ) : (

          <div className="py-7 text-center">
            <GitBranch
              size={24}
              className="mx-auto mb-2 text-navy-500"
            />

            <p className="text-xs text-navy-500">
              No roadmap milestones available.
            </p>
          </div>

        )}

        {roadmap.length > 0 && (
          <div className="mt-4 flex items-center justify-between rounded-lg bg-[#f8f1eb] px-3 py-3 dark:bg-white/[.04]">

            <span className="text-[10px] text-navy-500">
              Completed milestones
            </span>

            <span className="text-xs font-semibold text-[#80503d] dark:text-[#d9b8a5]">
              {completedRoadmap} / {roadmap.length}
            </span>

          </div>
        )}

      </section>

      {/* WORKSPACE SUMMARY */}

      <section className="grid gap-3 sm:grid-cols-2">

        <div className="card flex items-center gap-3 p-4">

          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f0e2d8] text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
            <ClipboardList size={18} />
          </div>

          <div>
            <p className="text-lg font-semibold text-[#211815] dark:text-white">
              {prds.length}
            </p>

            <p className="text-[10px] text-navy-500">
              Available PRDs
            </p>
          </div>

        </div>

        <div className="card flex items-center gap-3 p-4">

          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f0e2d8] text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]">
            <Package size={18} />
          </div>

          <div>
            <p className="text-lg font-semibold text-[#211815] dark:text-white">
              {roadmap.length}
            </p>

            <p className="text-[10px] text-navy-500">
              Roadmap initiatives
            </p>
          </div>

        </div>

      </section>

      {/* AI ASSISTANT CTA */}

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#d9c4b5] bg-[#f3e8df] px-4 py-4 text-[#634638] dark:border-white/10 dark:bg-white/[.04] dark:text-[#d9b8a5]">

        <div className="flex items-center gap-3">

          <div className="grid h-9 w-9 place-items-center rounded-lg bg-white/60 dark:bg-white/10">
            <Terminal size={17} />
          </div>

          <div>
            <p className="text-xs font-semibold">
              Need help understanding a product requirement?
            </p>

            <p className="mt-1 text-[10px]">
              Use the AI Assistant for product-related questions.
            </p>
          </div>

        </div>

        <Link
          to="/chat"
          className="inline-flex items-center gap-1 text-[10px] font-semibold underline underline-offset-4"
        >
          Open AI Assistant
          <ArrowUpRight size={12} />
        </Link>

      </section>

    </div>
  );
}
