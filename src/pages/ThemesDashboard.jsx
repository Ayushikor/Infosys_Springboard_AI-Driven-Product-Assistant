import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Sparkles, RefreshCw, FileText, X } from 'lucide-react';

import { useAppData } from '../context/AppDataContext';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';
import { formatDate } from '../utils/formatters';

const getThemeList = (run) => {
  const result = run?.results?.themes ?? run?.themes ?? null;
  if (Array.isArray(result)) return result;
  if (Array.isArray(result?.themes)) return result.themes;
  return [];
};

const getRunPayload = (response) => {
  if (!response || typeof response !== 'object') return null;
  return response.data?.data ?? response.data ?? response.result ?? response;
};

export default function ThemesDashboard() {
  const {
    raw,
    loading,
    error,
    analysis = {},
    runAnalysis,
    refreshDatasets,
  } = useAppData();

  const [search, setSearch] = useState('');
  const [minCount, setMinCount] = useState(0);
  const [sortBy, setSortBy] = useState('count');
  const [active, setActive] = useState(null);
  const [selectedImportId, setSelectedImportId] = useState('');
  const [analysisMessage, setAnalysisMessage] = useState('');
  const [localRun, setLocalRun] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const datasets = Array.isArray(analysis.datasets) ? analysis.datasets : [];
  const selectedDataset = datasets.find((item) => item.import_id === selectedImportId);

  useEffect(() => {
    if (!selectedImportId && datasets.length > 0) {
      setSelectedImportId(datasets[0].import_id);
    }
  }, [datasets, selectedImportId]);

  // Never show a different CSV's results just because it was analyzed most recently.
  const latestRun =
    localRun?.import_id === selectedImportId
      ? localRun
      : analysis.latest?.import_id === selectedImportId
        ? analysis.latest
        : null;

  const aiThemes = useMemo(() => getThemeList(latestRun), [latestRun]);
  const feedbackRecords = Array.isArray(raw?.feedback) ? raw.feedback : [];
  const feedbackById = useMemo(() => {
    const map = new Map();
    feedbackRecords.forEach((item) => {
      if (item?.id !== undefined && item?.id !== null) {
        map.set(String(item.id), item);
      }
    });
    return map;
  }, [feedbackRecords]);

  const stats = useMemo(() => {
    return aiThemes.map((theme, index) => {
      const feedbackIds = Array.isArray(theme.feedback_ids) ? theme.feedback_ids : [];
      const items = feedbackIds.map((id) => feedbackById.get(String(id)) || {
        id: String(id),
        title: String(id),
        message: '',
      });
      return {
        id: `${latestRun?.run_id || latestRun?.id || selectedImportId}-theme-${index}`,
        name: theme.name || `Theme ${index + 1}`,
        description: theme.description || 'No description was returned by the theme extraction agent.',
        keywords: Array.isArray(theme.keywords) ? theme.keywords : [],
        feedbackIds,
        items,
        count: feedbackIds.length,
      };
    });
  }, [aiThemes, feedbackById, latestRun, selectedImportId]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return stats
      .filter((theme) =>
        !query ||
        theme.name.toLowerCase().includes(query) ||
        theme.description.toLowerCase().includes(query) ||
        theme.keywords.some((keyword) => String(keyword).toLowerCase().includes(query))
      )
      .filter((theme) => theme.count >= minCount)
      .sort((a, b) => {
        if (sortBy === 'name') return a.name.localeCompare(b.name);
        return b.count - a.count;
      });
  }, [stats, search, minCount, sortBy]);

  const onRefreshDatasets = async () => {
    setRefreshing(true);
    setAnalysisMessage('');
    try {
      const response = await refreshDatasets();
      if (!response?.success) {
        setAnalysisMessage(response?.message || 'Could not refresh uploaded datasets.');
      }
    } catch (err) {
      setAnalysisMessage(err?.message || 'Could not refresh uploaded datasets.');
    } finally {
      setRefreshing(false);
    }
  };

  const onAnalyze = async () => {
    if (!selectedImportId) {
      setAnalysisMessage('Select an uploaded CSV before starting analysis.');
      return;
    }

    setAnalysisMessage('');
    setLocalRun(null);
    try {
      // This is the same dataset-scoped pipeline call used by the main Dashboard.
      const response = await runAnalysis(null, selectedImportId);
      if (response?.success) {
        const payload = getRunPayload(response);
        if (payload && typeof payload === 'object') {
          setLocalRun({ ...payload, import_id: payload.import_id || selectedImportId });
        }
        setAnalysisMessage(`AI theme extraction completed for ${selectedDataset?.fileName || 'the selected dataset'}.`);
      } else {
        setAnalysisMessage(response?.message || 'AI analysis failed.');
      }
    } catch (err) {
      setAnalysisMessage(err?.message || 'AI analysis failed.');
    }
  };

  if (loading) return <div className="card h-64 animate-pulse" />;
  if (error) return <EmptyState title="Could not load themes" description={error} />;
  if (!raw) return null;

  const running = Boolean(analysis.running);
  const datasetsLoading = Boolean(analysis.datasetsLoading || refreshing);

  return (
    <div className="space-y-5">
      <section className="card space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles size={16} className="text-accent" /> AI-extracted themes
            </div>
            <p className="mt-1 text-xs text-navy-500">
              Themes and feedback assignments are taken from Agent 1's saved analysis output. No local keyword-based fallback is used.
            </p>
          </div>
          <Button variant="outline" onClick={onRefreshDatasets} loading={datasetsLoading}>
            <RefreshCw size={15} className="mr-2" /> Refresh datasets
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
          <div>
            <label htmlFor="themes-dataset" className="mb-1.5 block text-xs font-medium text-navy-500">
              Select uploaded CSV
            </label>
            <select
              id="themes-dataset"
              value={selectedImportId}
              onChange={(event) => {
                setSelectedImportId(event.target.value);
                setLocalRun(null);
                setActive(null);
                setAnalysisMessage('');
              }}
              disabled={datasetsLoading || running}
              className="input w-full"
            >
              <option value="">Select a dataset</option>
              {datasets.map((dataset) => (
                <option key={dataset.import_id} value={dataset.import_id}>
                  {dataset.fileName} ({Number(dataset.recordCount || 0).toLocaleString()} records)
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button onClick={onAnalyze} loading={running} disabled={!selectedImportId || datasetsLoading || running}>
              <Sparkles size={15} className="mr-2" /> Run AI Analysis
            </Button>
          </div>
        </div>

        {analysis.datasetsError && <p className="text-sm text-rose-500">{analysis.datasetsError}</p>}
        {analysisMessage && <p className="text-sm text-navy-500" role="status">{analysisMessage}</p>}
        {selectedDataset && (
          <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-navy-800">
            <p className="font-medium">{selectedDataset.fileName}</p>
            <p className="mt-1 text-xs text-navy-500">
              {Number(selectedDataset.recordCount || 0).toLocaleString()} records
              {selectedDataset.importedAt ? ` · Uploaded ${formatDate(selectedDataset.importedAt)}` : ''}
            </p>
          </div>
        )}
        {!datasetsLoading && datasets.length === 0 && (
          <p className="text-sm text-navy-500">
            No uploaded datasets found. <Link to="/feedback/upload" className="font-medium text-accent">Upload a CSV file</Link> to begin.
          </p>
        )}
      </section>

      <section className="card flex flex-wrap items-end gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-[34px] text-navy-500" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search AI themes or keywords"
            className="input pl-9"
            aria-label="Search themes"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="themes-min-count">Min. feedback</label>
          <select id="themes-min-count" value={minCount} onChange={(event) => setMinCount(Number(event.target.value))} className="input py-2">
            <option value={0}>Any</option>
            <option value={1}>1+</option>
            <option value={3}>3+</option>
            <option value={5}>5+</option>
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-navy-500" htmlFor="themes-sort">Sort by</label>
          <select id="themes-sort" value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="input py-2">
            <option value="count">Feedback count</option>
            <option value="name">Name</option>
          </select>
        </div>
      </section>

      {!selectedImportId ? (
        <EmptyState title="Select a dataset" description="Choose an uploaded CSV above to run AI theme extraction." />
      ) : !latestRun ? (
        <EmptyState
          title="No AI theme results for this dataset"
          description="Run AI Analysis to execute the existing four-agent pipeline against the selected CSV. Results from other datasets are not shown here."
        />
      ) : aiThemes.length === 0 ? (
        <EmptyState title="No themes returned" description="The selected analysis run does not contain any saved Agent 1 themes." />
      ) : visible.length === 0 ? (
        <EmptyState title="No themes match your filters" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((theme) => (
            <button
              key={theme.id}
              type="button"
              onClick={() => setActive(theme)}
              className="card group flex flex-col p-5 text-left transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-semibold group-hover:text-accent">{theme.name}</h3>
                <span className="shrink-0 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 dark:bg-navy-700 dark:text-indigo-200">
                  {theme.count} feedback
                </span>
              </div>
              <p className="mt-2 line-clamp-3 text-sm text-navy-500">{theme.description}</p>
              {theme.keywords.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {theme.keywords.slice(0, 5).map((keyword, index) => (
                    <span key={`${theme.id}-keyword-${index}`} className="rounded-md bg-slate-100 px-2 py-1 text-[11px] text-navy-600 dark:bg-navy-800 dark:text-navy-200">
                      {keyword}
                    </span>
                  ))}
                  {theme.keywords.length > 5 && <span className="px-1 py-1 text-[11px] text-navy-500">+{theme.keywords.length - 5} more</span>}
                </div>
              )}
              <div className="mt-auto flex items-center gap-2 border-t border-slate-100 pt-4 text-xs text-navy-500 dark:border-navy-700">
                <FileText size={14} /> {theme.feedbackIds.length} source feedback IDs
              </div>
            </button>
          ))}
        </div>
      )}

      <ThemeDetailModal theme={active} onClose={() => setActive(null)} />
    </div>
  );
}

function ThemeDetailModal({ theme, onClose }) {
  if (!theme) return null;

  return (
    <Modal
      open
      onClose={onClose}
      title={theme.name}
      wide
      footer={<Button variant="outline" onClick={onClose}><X size={14} className="mr-2" /> Close</Button>}
    >
      <p className="text-sm text-navy-500">{theme.description}</p>

      <div className="mt-4 rounded-lg bg-slate-50 p-3 dark:bg-navy-900/40">
        <p className="text-xl font-semibold">{theme.count}</p>
        <p className="text-xs text-navy-500">Feedback records assigned by the AI theme extraction agent</p>
      </div>

      {theme.keywords.length > 0 && (
        <>
          <h3 className="mt-5 text-sm font-semibold">AI-extracted keywords</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {theme.keywords.map((keyword, index) => (
              <span key={`${theme.id}-detail-keyword-${index}`} className="rounded-md bg-slate-100 px-2.5 py-1.5 text-xs dark:bg-navy-800">{keyword}</span>
            ))}
          </div>
        </>
      )}

      <h3 className="mt-5 text-sm font-semibold">Related feedback</h3>
      {theme.items.length === 0 ? (
        <p className="mt-2 text-sm text-navy-500">The AI output did not assign feedback IDs to this theme.</p>
      ) : (
        <ul className="mt-2 max-h-72 divide-y divide-slate-100 overflow-y-auto dark:divide-navy-700">
          {theme.items.map((item, index) => (
            <li key={`${theme.id}-${item.id}-${index}`} className="py-3">
              <p className="text-sm font-medium">{item.title || item.id || 'Feedback record'}</p>
              {item.message && <p className="mt-1 whitespace-pre-wrap text-sm text-navy-500">{item.message}</p>}
              <p className="mt-1 text-xs text-navy-500">
                ID: {item.id}
                {item.createdAt ? ` · ${formatDate(item.createdAt)}` : ''}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
