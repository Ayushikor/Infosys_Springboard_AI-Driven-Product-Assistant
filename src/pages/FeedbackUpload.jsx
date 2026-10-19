import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { UploadCloud, FileText, X, CheckCircle2, AlertCircle, History } from 'lucide-react';
import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';
import { parseFeedbackFile, MAX_FILE_BYTES } from '../utils/csvParser';
import { formatBytes, formatDateTime } from '../utils/formatters';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';

const HISTORY_KEY = 'copilot.uploadHistory';
const readHistory = () => { try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; } catch { return []; } };
const writeHistory = (h) => { try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, 20))); } catch { /* ignore */ } };

export default function FeedbackUpload() {
  const { refresh } = useAppData();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState(null); // { rows, fatal }
  const [message, setMessage] = useState(null); // { type, text }
  const [importing, setImporting] = useState(false);
  const [history, setHistory] = useState(readHistory);

  // Reads and validates the selected file. All processing happens in the browser.
  const handleFile = async (f) => {
    setMessage(null);
    setParsed(null);
    setProgress(0);
    if (!f) return;
    setFile(f);
    setParsing(true);

    // Show real read progress by ticking while the file is read.
    const tick = setInterval(() => setProgress((p) => Math.min(90, p + 15)), 80);
    try {
      const result = await parseFeedbackFile(f);
      setParsed(result);
      if (result.fatal) setMessage({ type: 'error', text: result.fatal });
    } catch (err) {
      setMessage({ type: 'error', text: `Could not read the file: ${err.message}` });
    } finally {
      clearInterval(tick);
      setProgress(100);
      setParsing(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  const clearFile = () => {
    setFile(null); setParsed(null); setProgress(0); setMessage(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const validRows = parsed?.rows.filter((r) => r.errors.length === 0) ?? [];
  const invalidRows = parsed?.rows.filter((r) => r.errors.length > 0) ?? [];

  const onImport = async () => {
    if (!validRows.length) return;
    setImporting(true);
    const res = await apiClient.feedback.importMany(validRows.map((r) => r.record));
    setImporting(false);
    if (!res.success) {
      setMessage({ type: 'error', text: res.message });
      return;
    }
    const { added, skipped } = res.data;
    const text = `Imported ${added} record(s) from ${file.name}.${skipped ? ` ${skipped} duplicate ID(s) skipped.` : ''}${invalidRows.length ? ` ${invalidRows.length} invalid row(s) excluded.` : ''}`;
    setMessage({ type: 'success', text });
    const entry = { id: `up-${Date.now()}`, fileName: file.name, size: file.size, added, skipped, invalid: invalidRows.length, at: new Date().toISOString() };
    const next = [entry, ...history];
    setHistory(next);
    writeHistory(next);
    await refresh(); // dashboard, themes, feedback list all update from the shared state
    clearFile();
    setMessage({ type: 'success', text });
  };

  const previewRows = parsed?.rows.slice(0, 8) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-navy-500">Import customer feedback from CSV or JSON. Files are parsed in your browser and never uploaded.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Upload feedback file"
            className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${dragging ? 'border-accent bg-indigo-50 dark:bg-indigo-500/10' : 'border-slate-300 bg-white hover:border-accent/60 dark:border-navy-700 dark:bg-navy-800'}`}
          >
            <UploadCloud size={36} className="mx-auto text-accent" />
            <p className="mt-3 text-sm font-medium">Drag and drop a file here, or <span className="text-accent">browse</span></p>
            <p className="mt-1 text-xs text-navy-500">.csv or .json · max {formatBytes(MAX_FILE_BYTES)}</p>
            <input ref={inputRef} type="file" accept=".csv,.json,text/csv,application/json" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
          </div>

          {file && (
            <div className="card p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-indigo-50 p-2 text-accent dark:bg-indigo-500/15"><FileText size={18} /></div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-navy-500">{formatBytes(file.size)}{parsed && !parsed.fatal && ` · ${parsed.rows.length} rows detected`}</p>
                </div>
                <button onClick={clearFile} className="btn-ghost p-1.5" aria-label="Remove file"><X size={16} /></button>
              </div>
              {(parsing || progress > 0) && (
                <div className="mt-3">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-navy-700" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
                    <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-200" style={{ width: `${progress}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-navy-500">{parsing ? 'Parsing file…' : 'Ready'}</p>
                </div>
              )}
            </div>
          )}

          {message && (
            <div role={message.type === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2 rounded-lg border p-3 text-sm ${message.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300' : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300'}`}>
              {message.type === 'error' ? <AlertCircle size={16} className="mt-0.5 shrink-0" /> : <CheckCircle2 size={16} className="mt-0.5 shrink-0" />}
              <span>{message.text}</span>
            </div>
          )}

          {/* Preview */}
          {parsed && !parsed.fatal && (
            <div className="card overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-navy-700">
                <div>
                  <h2 className="text-sm font-semibold">Preview</h2>
                  <p className="text-xs text-navy-500">Showing {previewRows.length} of {parsed.rows.length}. {validRows.length} valid · {invalidRows.length} invalid</p>
                </div>
                <Button onClick={onImport} loading={importing} disabled={!validRows.length}>Import {validRows.length} record(s)</Button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-navy-500 dark:bg-navy-900/40">
                    <tr><th className="px-4 py-2">Row</th><th className="px-4 py-2">Title</th><th className="px-4 py-2">Customer</th><th className="px-4 py-2">Sentiment</th><th className="px-4 py-2">Theme</th><th className="px-4 py-2">Votes</th><th className="px-4 py-2">Status</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-navy-700">
                    {previewRows.map((r) => (
                      <tr key={r.rowNumber}>
                        <td className="px-4 py-2 text-navy-500">{r.rowNumber}</td>
                        <td className="max-w-[200px] truncate px-4 py-2">{r.record.title || '—'}</td>
                        <td className="px-4 py-2">{r.record.customer}</td>
                        <td className="px-4 py-2"><Badge tone={r.record.sentiment}>{r.record.sentiment}</Badge></td>
                        <td className="px-4 py-2">{r.record.theme}</td>
                        <td className="px-4 py-2 tabular-nums">{r.record.votes}</td>
                        <td className="px-4 py-2">{r.errors.length ? <span className="text-xs text-rose-600">{r.errors.join(', ')}</span> : <span className="text-xs text-emerald-600">OK</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Expected format */}
          <div className="card p-5 text-sm">
            <h2 className="mb-2 font-semibold">Expected fields</h2>
            <p className="text-navy-500"><code className="rounded bg-slate-100 px-1 dark:bg-navy-700">title</code> and <code className="rounded bg-slate-100 px-1 dark:bg-navy-700">message</code> are required. Optional: <code>id, customer, source, createdAt, sentiment, theme, votes</code>. Missing optional fields get sensible defaults.</p>
            <p className="mt-2 text-navy-500">JSON accepts an array of objects or <code>{'{ "feedback": [ ... ] }'}</code>.</p>
          </div>
        </div>

        {/* History */}
        <div className="card h-fit p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold"><History size={16} />Upload history</div>
          {history.length === 0 ? <p className="text-sm text-navy-500">No uploads yet this session.</p> : (
            <ul className="space-y-3">
              {history.map((h) => (
                <li key={h.id} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-navy-700">
                  <p className="truncate font-medium">{h.fileName}</p>
                  <p className="text-xs text-navy-500">{formatDateTime(h.at)} · {formatBytes(h.size)}</p>
                  <p className="mt-1 text-xs"><span className="text-emerald-600">+{h.added} added</span>{h.skipped > 0 && <span className="text-navy-500"> · {h.skipped} skipped</span>}{h.invalid > 0 && <span className="text-rose-600"> · {h.invalid} invalid</span>}</p>
                </li>
              ))}
            </ul>
          )}
          <Link to="/feedback" className="mt-4 inline-block text-sm font-medium text-accent">View feedback list →</Link>
        </div>
      </div>
    </div>
  );
}
