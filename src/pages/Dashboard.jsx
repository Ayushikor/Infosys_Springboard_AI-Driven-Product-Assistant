
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";

import {
  MessageSquareText,
  Tags,
  ListOrdered,
  FileText,
  Upload,
  Sparkles,
  ListChecks,
  FilePlus2,
} from "lucide-react";

import { useAppData } from "../context/AppDataContext";
import { useTheme } from "../context/ThemeContext";

import Badge from "../components/common/Badge";
import EmptyState from "../components/common/EmptyState";

import {
  formatDate,
  timeAgo,
} from "../utils/formatters";


// ---------------------------------------------------------
// CONSTANTS
// ---------------------------------------------------------

const SENTIMENT_COLORS = {
  positive: "#10b981",
  neutral: "#94a3b8",
  negative: "#f43f5e",
};


// ---------------------------------------------------------
// FEEDBACK TREND
// ---------------------------------------------------------

const buildTrend = (feedback = []) => {

  const days = Array.from(
    { length: 14 },
    (_, i) => {

      const date = new Date();

      date.setHours(0, 0, 0, 0);

      date.setDate(
        date.getDate() - (13 - i)
      );

      return {
        key: date.toDateString(),

        label: date.toLocaleDateString(
          undefined,
          {
            month: "short",
            day: "numeric",
          }
        ),

        count: 0,
      };
    }
  );

  feedback.forEach((item) => {

    if (!item.createdAt) {
      return;
    }

    const key = new Date(
      item.createdAt
    ).toDateString();

    const matchingDay = days.find(
      (day) => day.key === key
    );

    if (matchingDay) {
      matchingDay.count += 1;
    }
  });

  return days;
};


// ---------------------------------------------------------
// STAT CARD
// ---------------------------------------------------------

function StatCard({
  label,
  value,
  icon: Icon,
  to,
  tone,
}) {

  return (
    <Link
      to={to}
      className="card group p-5 transition hover:-translate-y-0.5 hover:shadow-md"
    >

      <div className="flex items-center justify-between">

        <p className="text-sm text-navy-500">
          {label}
        </p>

        <div className={`rounded-lg p-2 ${tone}`}>
          <Icon size={16} />
        </div>

      </div>

      <p className="mt-3 text-2xl font-semibold tabular-nums">
        {value}
      </p>

    </Link>
  );
}


// ---------------------------------------------------------
// DASHBOARD
// ---------------------------------------------------------

export default function Dashboard() {

  const {
    raw,
    derived,
    loading,
    error,
    analysis,
    runAnalysis,
    refreshDatasets,
  } = useAppData();

  const { isDark } = useTheme();

  const [analysisMessage, setAnalysisMessage] = useState("");

  const [selectedImportId, setSelectedImportId] = useState("");

  // -------------------------------------------------------
  // DATASET STATE
  // -------------------------------------------------------

  const uploadedDatasets = analysis.datasets || [];

  const selectedDataset = uploadedDatasets.find(
    (dataset) => dataset.import_id === selectedImportId
  );

  // -------------------------------------------------------
  // LATEST AI ANALYSIS
  // -------------------------------------------------------

  const latestAnalysis = analysis.latest;

  const aiResults = latestAnalysis?.results || {};

  const agentStatus = latestAnalysis?.agent_status || {};

  // -------------------------------------------------------
  // AI METRICS
  // -------------------------------------------------------

  const aiMetrics = [
    {
      label: "Themes Extracted",
      count:
        aiResults.themes?.themes?.length ?? 0,
    },
    {
      label: "Pain Point Groups",
      count:
        aiResults.pain_points?.pain_points?.length ?? 0,
    },
    {
      label: "Feature Clusters",
      count:
        aiResults.feature_clusters?.clusters?.length ?? 0,
    },
    {
      label: "Trends Identified",
      count:
        aiResults.trends?.total_trends_identified ??
        aiResults.trends?.trends?.length ??
        0,
    },
  ];

  // -------------------------------------------------------
  // RUN DATASET-SPECIFIC AI ANALYSIS
  // -------------------------------------------------------

  const handleRunAnalysis = async () => {

    setAnalysisMessage("");

    if (!selectedImportId) {

      setAnalysisMessage(
        "Please select an uploaded dataset first."
      );

      return;
    }

    const response = await runAnalysis(
      null,
      selectedImportId
    );

    setAnalysisMessage(
      response.success
        ? `Analysis results saved successfully for ${
            selectedDataset?.fileName || "the selected dataset"
          }.`
        : response.message || "Analysis failed."
    );
  };


  // -------------------------------------------------------
  // REFRESH DATASETS
  // -------------------------------------------------------

  const handleRefreshDatasets = async () => {

    setAnalysisMessage("");

    const response = await refreshDatasets();

    if (!response.success) {
      setAnalysisMessage(
        response.message || "Could not refresh datasets."
      );
    }
  };


  // -------------------------------------------------------
  // LOADING AND ERROR STATES
  // -------------------------------------------------------

  if (loading) {
    return (
      <div className="card h-64 animate-pulse" />
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Could not load dashboard"
        description={error}
      />
    );
  }

  if (!raw || !derived) {
    return null;
  }


  // -------------------------------------------------------
  // DERIVED DASHBOARD VALUES
  // -------------------------------------------------------

  const feedback = raw.feedback || [];
  const activity = raw.activity || [];

  const trend = buildTrend(feedback);

  const sentimentData = Object.entries(
    derived.sentiment || {}
  ).map(([key, value]) => ({
    name: key,
    value,
  }));

  const totalSent = sentimentData.reduce(
    (sum, item) => sum + item.value,
    0
  );

  const topThemes = derived.themeStats.slice(0, 5);

  const highPriority = derived.prioritized
    .filter((feature) => feature.priority === "High")
    .slice(0, 5);

  const recent = [...feedback]
    .sort(
      (a, b) =>
        new Date(b.createdAt) - new Date(a.createdAt)
    )
    .slice(0, 5);

  const gridColor = isDark
    ? "#2a3558"
    : "#e2e8f0";

  const tickColor = isDark
    ? "#b8c0d4"
    : "#64708f";

  const negShare = totalSent
    ? Math.round(
        ((derived.sentiment?.negative || 0) / totalSent) * 100
      )
    : 0;

  const topTheme = topThemes[0];

  const insight =
    topTheme && topTheme.count > 0
      ? `${topTheme.name} is the largest theme with ${
          topTheme.count
        } records (${topTheme.negativeShare}% negative). ${
          negShare
        }% of all feedback is negative overall.`
      : "Upload feedback to generate insights.";


  // -------------------------------------------------------
  // RENDER
  // -------------------------------------------------------

  return (

    <div className="space-y-6">

      {/* ----------------------------------------------- */}
      {/* QUICK ACTIONS */}
      {/* ----------------------------------------------- */}

      <div className="flex flex-wrap gap-2">

        <Link
          to="/feedback/upload"
          className="btn-outline"
        >
          <Upload size={16} />
          Upload Feedback
        </Link>

        <Link
          to="/themes"
          className="btn-outline"
        >
          <Tags size={16} />
          Analyze Themes
        </Link>

        <Link
          to="/prioritization"
          className="btn-outline"
        >
          <ListOrdered size={16} />
          Prioritize Features
        </Link>

        <Link
          to="/prd"
          className="btn-outline"
        >
          <FilePlus2 size={16} />
          Generate PRD
        </Link>

      </div>


      {/* ----------------------------------------------- */}
      {/* SUMMARY CARDS */}
      {/* ----------------------------------------------- */}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <StatCard
          label="Total Feedback"
          value={derived.feedbackCount}
          icon={MessageSquareText}
          to="/feedback"
          tone="bg-indigo-50 text-accent dark:bg-indigo-500/15"
        />

        <StatCard
          label="Active Themes"
          value={derived.activeThemes}
          icon={Tags}
          to="/themes"
          tone="bg-violet-50 text-violet-600 dark:bg-violet-500/15"
        />

        <StatCard
          label="Prioritized Features"
          value={derived.prioritizedCount}
          icon={ListOrdered}
          to="/prioritization"
          tone="bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15"
        />

        <StatCard
          label="Generated PRDs"
          value={derived.prdCount}
          icon={FileText}
          to="/prd"
          tone="bg-amber-50 text-amber-600 dark:bg-amber-500/15"
        />

      </div>


      {/* ----------------------------------------------- */}
      {/* FOUR-AGENT AI ANALYSIS */}
      {/* ----------------------------------------------- */}

      <div className="card p-5 space-y-5">

        {/* --------------------------------------------- */}
        {/* HEADER */}
        {/* --------------------------------------------- */}

        <div className="flex flex-col gap-4">

          <div>

            <div className="flex items-center gap-2">

              <Sparkles
                size={19}
                className="text-accent"
              />

              <h2 className="text-lg font-semibold">
                AI Feedback Intelligence
              </h2>

            </div>

            <p className="text-sm text-navy-500 mt-1">
              Insights generated by your four specialized AI agents.
            </p>

          </div>


          {/* ------------------------------------------- */}
          {/* DATASET SELECTOR */}
          {/* ------------------------------------------- */}

          <div className="flex flex-wrap items-end gap-3">

            <div className="min-w-0 flex-1">

              <label
                htmlFor="analysis-dataset"
                className="mb-2 block text-sm font-medium"
              >
                Select dataset to analyse
              </label>

              <select
                id="analysis-dataset"
                value={selectedImportId}
                onChange={(event) => {
                  setSelectedImportId(event.target.value);
                  setAnalysisMessage("");
                }}
                disabled={
                  analysis.datasetsLoading ||
                  analysis.running
                }
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy-800 outline-none focus:border-indigo-500 dark:border-navy-700 dark:bg-navy-800 dark:text-white"
              >

                <option value="">
                  Select an uploaded dataset
                </option>

                {uploadedDatasets.map((dataset) => (

                  <option
                    key={dataset.import_id}
                    value={dataset.import_id}
                  >
                    {dataset.fileName} (
                    {Number(
                      dataset.recordCount || 0
                    ).toLocaleString()} records)
                  </option>

                ))}

              </select>

            </div>


            {/* ----------------------------------------- */}
            {/* REFRESH DATASETS */}
            {/* ----------------------------------------- */}

            <button
              type="button"
              className="btn-outline"
              onClick={handleRefreshDatasets}
              disabled={
                analysis.datasetsLoading ||
                analysis.running
              }
            >
              {analysis.datasetsLoading
                ? "Loading..."
                : "Refresh datasets"}
            </button>


            {/* ----------------------------------------- */}
            {/* RUN ANALYSIS */}
            {/* ----------------------------------------- */}

            <button
              type="button"
              className="btn-primary"
              onClick={handleRunAnalysis}
              disabled={
                analysis.running ||
                analysis.loading ||
                analysis.datasetsLoading ||
                !selectedImportId
              }
            >

              <Sparkles size={16} />

              {analysis.running
                ? "Running Analysis..."
                : "Run AI Analysis"}

            </button>

          </div>


          {/* ------------------------------------------- */}
          {/* DATASET STATUS */}
          {/* ------------------------------------------- */}

          {analysis.datasetsError && (

            <p className="text-sm text-rose-500">
              {analysis.datasetsError}
            </p>

          )}

          {!analysis.datasetsLoading &&
            uploadedDatasets.length === 0 && (

              <p className="text-sm text-navy-500">

                No uploaded datasets found.{" "}

                <Link
                  to="/feedback/upload"
                  className="font-medium text-accent"
                >
                  Upload a CSV file
                </Link>

                {" "}to get started.

              </p>

            )}

          {selectedDataset && (

            <div className="rounded-lg bg-indigo-50 p-3 dark:bg-navy-800">

              <p className="text-sm font-medium">
                Selected dataset: {selectedDataset.fileName}
              </p>

              <p className="mt-1 text-xs text-navy-500">
                {Number(
                  selectedDataset.recordCount || 0
                ).toLocaleString()} records available for analysis
              </p>

              {selectedDataset.importedAt && (

                <p className="mt-1 text-xs text-navy-500">
                  Uploaded: {formatDate(selectedDataset.importedAt)}
                </p>

              )}

            </div>

          )}

        </div>


        {/* --------------------------------------------- */}
        {/* NOTIFICATIONS */}
        {/* --------------------------------------------- */}

        {analysisMessage && (

          <p
            role="status"
            className={`text-sm ${
              analysisMessage.toLowerCase().includes("failed") ||
              analysisMessage.toLowerCase().includes("could not") ||
              analysisMessage.toLowerCase().includes("select")
                ? "text-rose-500"
                : "text-emerald-600"
            }`}
          >
            {analysisMessage}
          </p>

        )}

        {analysis.error && (

          <p className="text-sm text-rose-500">
            {analysis.error}
          </p>

        )}


        {/* --------------------------------------------- */}
        {/* RUNNING STATE */}
        {/* --------------------------------------------- */}

        {analysis.running && (

          <div className="rounded-lg bg-indigo-50 dark:bg-navy-800 p-4">

            <div className="flex items-center gap-2">

              <Sparkles
                size={16}
                className="text-accent"
              />

              <p className="text-sm font-medium">
                Your AI agents are analysing the selected dataset...
              </p>

            </div>

            <p className="text-xs text-navy-500 mt-2">
              This may take a few minutes. Please keep this page open.
            </p>

            {selectedDataset && (

              <p className="text-xs text-navy-500 mt-1">
                Dataset: {selectedDataset.fileName}
              </p>

            )}

          </div>

        )}


        {/* --------------------------------------------- */}
        {/* LATEST ANALYSIS */}
        {/* --------------------------------------------- */}

        {latestAnalysis ? (

          <>

            {/* Run metadata */}

            <div className="flex flex-wrap items-center gap-3 text-xs text-navy-500">

              <span>
                Run ID: {latestAnalysis.run_id}
              </span>

              <Badge
                tone={
                  latestAnalysis.status === "completed"
                    ? "positive"
                    : latestAnalysis.status === "failed"
                      ? "negative"
                      : "neutral"
                }
              >
                {latestAnalysis.status}
              </Badge>

              <span>
                {latestAnalysis.total_feedback_analyzed || 0} records analysed
              </span>

              {latestAnalysis.import_id && (

                <span>
                  Dataset-specific analysis
                </span>

              )}

            </div>


            {/* AI metrics */}

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

              {aiMetrics.map((metric) => (

                <div
                  key={metric.label}
                  className="rounded-xl border border-slate-200 dark:border-navy-700 p-4"
                >

                  <p className="text-xs text-navy-500">
                    {metric.label}
                  </p>

                  <p className="mt-2 text-2xl font-semibold tabular-nums">
                    {metric.count}
                  </p>

                </div>

              ))}

            </div>


            {/* Individual agent statuses */}

            <div className="grid gap-3 sm:grid-cols-2">

              {[
                ["themes", "Agent 1 · Theme Extraction"],
                ["pain_points", "Agent 2 · Pain Point Identification"],
                ["feature_clusters", "Agent 3 · Feature Clustering"],
                ["trends", "Agent 4 · Trend Analysis"],
              ].map(([key, label]) => {

                const status = agentStatus[key];

                const successful = [
                  "completed",
                  "completed_no_candidates",
                ].includes(status);

                return (

                  <div
                    key={key}
                    className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 dark:bg-navy-800 p-3"
                  >

                    <span className="text-sm font-medium">
                      {label}
                    </span>

                    <Badge
                      tone={
                        successful
                          ? "positive"
                          : status === "failed"
                            ? "negative"
                            : "neutral"
                      }
                    >
                      {status || "Unknown"}
                    </Badge>

                  </div>

                );
              })}

            </div>


            {/* Token usage */}

            {latestAnalysis.token_usage && (

              <div className="border-t border-slate-200 dark:border-navy-700 pt-4">

                <h3 className="text-sm font-semibold">
                  AI Token Usage
                </h3>

                <p className="mt-2 text-2xl font-semibold tabular-nums">
                  {(
                    latestAnalysis.token_usage.total_tokens || 0
                  ).toLocaleString()}
                </p>

                <p className="text-xs text-navy-500">
                  Total provider-reported tokens
                </p>

              </div>

            )}

          </>

        ) : (

          <EmptyState
            icon={Sparkles}
            title="No AI analysis available"
            description={
              analysis.loading
                ? "Loading your saved analysis..."
                : "Select an uploaded dataset and run the four-agent pipeline to generate product insights."
            }
          />

        )}


        {/* --------------------------------------------- */}
        {/* ANALYSIS HISTORY */}
        {/* --------------------------------------------- */}

        {analysis.runs.length > 0 && (

          <div className="border-t border-slate-200 dark:border-navy-700 pt-4">

            <h3 className="font-semibold text-sm mb-3">
              Recent Analysis Runs
            </h3>

            <div className="space-y-2">

              {analysis.runs.slice(0, 5).map((run) => (

                <div
                  key={run.run_id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 dark:bg-navy-800 p-3 text-sm"
                >

                  <div>

                    <p className="font-medium">
                      {run.run_id}
                    </p>

                    <p className="text-xs text-navy-500">

                      {run.total_feedback_analyzed || 0} records

                      {run.createdAt
                        ? ` · ${formatDate(run.createdAt)}`
                        : ""}

                      {run.import_id
                        ? " · Uploaded dataset"
                        : ""}

                    </p>

                  </div>

                  <Badge
                    tone={
                      run.status === "completed"
                        ? "positive"
                        : run.status === "failed"
                          ? "negative"
                          : "neutral"
                    }
                  >
                    {run.status}
                  </Badge>

                </div>

              ))}

            </div>

          </div>

        )}

      </div>


      {/* ----------------------------------------------- */}
      {/* FEEDBACK TREND AND SENTIMENT */}
      {/* ----------------------------------------------- */}

      <div className="grid gap-6 xl:grid-cols-3">

        {/* Feedback trend */}

        <div className="card p-5 xl:col-span-2">

          <div className="mb-4 flex items-center justify-between">

            <h2 className="text-sm font-semibold">
              Feedback trend (14 days)
            </h2>

          </div>

          <div className="h-56">

            {feedback.length === 0 ? (

              <EmptyState
                title="No feedback yet"
                description="Upload a CSV or JSON file to see trends."
              />

            ) : (

              <ResponsiveContainer
                width="100%"
                height="100%"
              >

                <LineChart data={trend}>

                  <CartesianGrid
                    stroke={gridColor}
                    strokeDasharray="3 3"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="label"
                    tick={{
                      fill: tickColor,
                      fontSize: 11,
                    }}
                    tickLine={false}
                    axisLine={false}
                    interval={2}
                  />

                  <YAxis
                    allowDecimals={false}
                    tick={{
                      fill: tickColor,
                      fontSize: 11,
                    }}
                    tickLine={false}
                    axisLine={false}
                    width={28}
                  />

                  <Tooltip />

                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#6366f1"
                    strokeWidth={2.5}
                    dot={false}
                  />

                </LineChart>

              </ResponsiveContainer>

            )}

          </div>

        </div>


        {/* Sentiment distribution */}

        <div className="card p-5">

          <h2 className="mb-4 text-sm font-semibold">
            Sentiment distribution
          </h2>

          {totalSent === 0 ? (

            <EmptyState
              title="No sentiment data"
            />

          ) : (

            <div className="flex items-center gap-4">

              <div className="h-40 w-40 shrink-0">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <PieChart>

                    <Pie
                      data={sentimentData}
                      dataKey="value"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={3}
                      stroke="none"
                    >

                      {sentimentData.map((item) => (

                        <Cell
                          key={item.name}
                          fill={SENTIMENT_COLORS[item.name] || "#94a3b8"}
                        />

                      ))}

                    </Pie>

                    <Tooltip />

                  </PieChart>

                </ResponsiveContainer>

              </div>

              <ul className="space-y-2 text-sm">

                {sentimentData.map((item) => (

                  <li
                    key={item.name}
                    className="flex items-center gap-2"
                  >

                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{
                        background:
                          SENTIMENT_COLORS[item.name] || "#94a3b8",
                      }}
                    />

                    <span className="capitalize text-navy-500">
                      {item.name}
                    </span>

                    <span className="ml-auto font-medium tabular-nums">
                      {item.value}
                    </span>

                  </li>

                ))}

              </ul>

            </div>

          )}

        </div>

      </div>


      {/* ----------------------------------------------- */}
      {/* THEMES, INSIGHT AND HIGH-PRIORITY FEATURES */}
      {/* ----------------------------------------------- */}

      <div className="grid gap-6 xl:grid-cols-3">

        {/* Top themes */}

        <div className="card p-5">

          <div className="mb-4 flex items-center justify-between">

            <h2 className="text-sm font-semibold">
              Top product themes
            </h2>

            <Link
              to="/themes"
              className="text-xs font-medium text-accent"
            >
              View all
            </Link>

          </div>

          {topThemes.length === 0 ? (

            <p className="text-sm text-navy-500">
              No themes available yet.
            </p>

          ) : (

            <ul className="space-y-3">

              {topThemes.map((theme) => (

                <li key={theme.id}>

                  <div className="mb-1 flex justify-between text-sm">

                    <span className="truncate">
                      {theme.name}
                    </span>

                    <span className="tabular-nums text-navy-500">
                      {theme.count}
                    </span>

                  </div>

                  <div className="h-1.5 rounded-full bg-slate-100 dark:bg-navy-700">

                    <div
                      className="h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
                      style={{
                        width: `${Math.max(
                          0,
                          Math.min(
                            100,
                            theme.priorityScore || 0
                          )
                        )}%`,
                      }}
                    />

                  </div>

                </li>

              ))}

            </ul>

          )}

        </div>


        {/* Local insight */}

        <div className="card p-5">

          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">

            <Sparkles
              size={16}
              className="text-accent"
            />

            Insight

          </div>

          <p className="text-sm leading-relaxed text-navy-700 dark:text-slate-300">
            {insight}
          </p>

          <p className="mt-3 text-xs text-navy-500">
            Generated by local rules. No external AI service.
          </p>

          <Link
            to="/chat"
            className="mt-4 inline-block text-xs font-medium text-accent"
          >
            Ask the copilot →
          </Link>

        </div>


        {/* High-priority features */}

        <div className="card p-5">

          <div className="mb-4 flex items-center justify-between">

            <h2 className="text-sm font-semibold">
              High-priority features
            </h2>

            <Link
              to="/prioritization"
              className="text-xs font-medium text-accent"
            >
              View all
            </Link>

          </div>

          {highPriority.length === 0 ? (

            <p className="text-sm text-navy-500">
              No high-priority features yet.
            </p>

          ) : (

            <ul className="divide-y divide-slate-100 dark:divide-navy-700">

              {highPriority.map((feature) => (

                <li
                  key={feature.id}
                  className="flex items-center justify-between py-2.5 text-sm"
                >

                  <span className="truncate pr-2">
                    {feature.name}
                  </span>

                  <span className="tabular-nums text-navy-500">
                    RICE {feature.rice}
                  </span>

                </li>

              ))}

            </ul>

          )}

        </div>

      </div>


      {/* ----------------------------------------------- */}
      {/* RECENT FEEDBACK AND ACTIVITY */}
      {/* ----------------------------------------------- */}

      <div className="grid gap-6 xl:grid-cols-3">

        {/* Recent feedback */}

        <div className="card overflow-hidden xl:col-span-2">

          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-navy-700">

            <h2 className="text-sm font-semibold">
              Recent feedback
            </h2>

            <Link
              to="/feedback"
              className="text-xs font-medium text-accent"
            >
              View all
            </Link>

          </div>

          {recent.length === 0 ? (

            <EmptyState
              icon={ListChecks}
              title="No feedback yet"
              description="Import a CSV or JSON file to get started."
              action={
                <Link
                  to="/feedback/upload"
                  className="btn-primary"
                >
                  Upload feedback
                </Link>
              }
            />

          ) : (

            <div className="overflow-x-auto">

              <table className="min-w-full text-sm">

                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-navy-500 dark:bg-navy-900/40">

                  <tr>

                    <th className="px-5 py-2.5">
                      Title
                    </th>

                    <th className="px-5 py-2.5">
                      Customer
                    </th>

                    <th className="px-5 py-2.5">
                      Sentiment
                    </th>

                    <th className="px-5 py-2.5">
                      Date
                    </th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-100 dark:divide-navy-700">

                  {recent.map((item) => (

                    <tr
                      key={item.id}
                      className="hover:bg-slate-50 dark:hover:bg-navy-700/50"
                    >

                      <td className="max-w-[260px] truncate px-5 py-3 font-medium">
                        {item.title}
                      </td>

                      <td className="px-5 py-3 text-navy-500">
                        {item.customer || "Unknown"}
                      </td>

                      <td className="px-5 py-3">

                        <Badge tone={item.sentiment}>
                          {item.sentiment}
                        </Badge>

                      </td>

                      <td className="whitespace-nowrap px-5 py-3 text-navy-500">
                        {formatDate(item.createdAt)}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </div>


        {/* Recent activity */}

        <div className="card p-5">

          <h2 className="mb-4 text-sm font-semibold">
            Recent activity
          </h2>

          {activity.length === 0 ? (

            <p className="text-sm text-navy-500">
              No activity yet.
            </p>

          ) : (

            <ul className="space-y-4">

              {activity.slice(0, 6).map((item) => (

                <li
                  key={item.id}
                  className="flex gap-3 text-sm"
                >

                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />

                  <div className="min-w-0">

                    <p className="text-navy-700 dark:text-slate-300">
                      {item.text}
                    </p>

                    <p className="text-xs text-navy-500">
                      {timeAgo(item.at)}
                    </p>

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
