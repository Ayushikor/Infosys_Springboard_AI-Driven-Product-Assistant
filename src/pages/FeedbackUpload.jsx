
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  UploadCloud,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  History,
} from 'lucide-react';

import { apiClient } from '../api/apiClient';
import { useAppData } from '../context/AppDataContext';

import {
  parseFeedbackFile,
  MAX_FILE_BYTES,
} from '../utils/csvParser';

import {
  formatBytes,
  formatDateTime,
} from '../utils/formatters';

import Button from '../components/common/Button';
import Badge from '../components/common/Badge';

// ---------------------------------------------------------
// UPLOAD HISTORY
// ---------------------------------------------------------

const HISTORY_KEY = 'copilot.uploadHistory';

const readHistory = () => {
  try {
    const history = JSON.parse(
      localStorage.getItem(HISTORY_KEY)
    );

    return Array.isArray(history) ? history : [];
  } catch {
    return [];
  }
};

const writeHistory = (history) => {
  try {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify(history.slice(0, 20))
    );
  } catch (error) {
    console.warn('Could not save upload history:', error);
  }
};

// ---------------------------------------------------------
// COMPONENT
// ---------------------------------------------------------

export default function FeedbackUpload() {
  const { refresh } = useAppData();

  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [message, setMessage] = useState(null);
  const [importing, setImporting] = useState(false);
  const [history, setHistory] = useState(readHistory);

  // -------------------------------------------------------
  // FILE PARSING
  // -------------------------------------------------------

  const handleFile = async (selectedFile) => {
    setMessage(null);
    setParsed(null);
    setProgress(0);

    if (!selectedFile) return;

    setFile(selectedFile);
    setParsing(true);

    const tick = setInterval(() => {
      setProgress((current) =>
        Math.min(90, current + 15)
      );
    }, 80);

    try {
      const result = await parseFeedbackFile(selectedFile);

      setParsed(result);

      if (result.fatal) {
        setMessage({
          type: 'error',
          text: result.fatal,
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: `Could not read the file: ${error.message}`,
      });
    } finally {
      clearInterval(tick);
      setProgress(100);
      setParsing(false);
    }
  };

  // -------------------------------------------------------
  // DRAG AND DROP
  // -------------------------------------------------------

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFile(droppedFile);
    }
  };

  // -------------------------------------------------------
  // CLEAR SELECTED FILE
  // -------------------------------------------------------

  const clearFile = ({ preserveMessage = false } = {}) => {
    setFile(null);
    setParsed(null);
    setProgress(0);

    if (!preserveMessage) {
      setMessage(null);
    }

    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  // -------------------------------------------------------
  // VALIDATION RESULTS
  // -------------------------------------------------------

  const validRows =
    parsed?.rows.filter((row) => row.errors.length === 0) ?? [];

  const invalidRows =
    parsed?.rows.filter((row) => row.errors.length > 0) ?? [];

  const previewRows = parsed?.rows.slice(0, 8) ?? [];

  // -------------------------------------------------------
  // IMPORT FEEDBACK
  // -------------------------------------------------------

  const onImport = async () => {
    if (!validRows.length || importing || !file) {
      return;
    }

    setImporting(true);

    try {
      // Send only frontend-validated records.
      const records = validRows.map((row) => row.record);

      // Pass filename to create a separate dataset import.
      const response = await apiClient.feedback.importMany(
        records,
        file.name
      );

      // Handle API-level errors.
      if (!response?.success) {
        setMessage({
          type: 'error',
          text:
            response?.message ||
            'Import failed. Please try again.',
        });

        return;
      }

      // Read actual backend response.
      const submitted = records.length;

      const added = Math.max(
        0,
        Number(response.data?.added) || 0
      );

      const skipped = Math.max(
        0,
        Number(response.data?.skipped) || 0
      );

      const invalid = invalidRows.length;

      const accountedFor = added + skipped;

      const unaccounted = Math.max(
        0,
        submitted - accountedFor
      );

      let type = 'success';

      const parts = [];

      if (
        added === submitted &&
        skipped === 0 &&
        invalid === 0
      ) {
        type = 'success';

        parts.push(
          `Successfully imported all ${added} record(s) from ${file.name}.`
        );
      } else if (added === 0 && skipped > 0) {
        type = 'warning';

        parts.push(
          `No new records imported. ${skipped} record(s) were skipped because they already exist or failed backend validation.`
        );
      } else if (added > 0 && skipped > 0) {
        type = 'warning';

        parts.push(
          `Imported ${added} new record(s). ${skipped} record(s) were skipped because they already exist or failed backend validation.`
        );
      } else if (added > 0) {
        type = 'warning';

        parts.push(
          `Imported ${added} record(s).`
        );
      } else {
        type = 'warning';

        parts.push(
          'The backend accepted the request but did not report any imported records.'
        );
      }

      if (invalid > 0) {
        type = 'warning';

        parts.push(
          `${invalid} invalid row(s) were excluded before import.`
        );
      }

      if (unaccounted > 0) {
        type = 'warning';

        parts.push(
          `${unaccounted} record(s) were not accounted for in the backend response.`
        );
      }

      const resultText = parts.join(' ');

      // ---------------------------------------------------
      // SAVE UPLOAD HISTORY
      // ---------------------------------------------------

      const entry = {
        id: `up-${Date.now()}`,
        fileName: file.name,
        size: file.size,
        added,
        skipped,
        invalid,
        submitted,
        importId: response.data?.import_id || null,
        at: new Date().toISOString(),
      };

      const nextHistory = [entry, ...history];

      setHistory(nextHistory);
      writeHistory(nextHistory);

      // ---------------------------------------------------
      // REFRESH APPLICATION DATA
      // ---------------------------------------------------

      let refreshFailed = false;

      try {
        await refresh();
      } catch (refreshError) {
        console.error(
          'Records were imported, but application data could not refresh:',
          refreshError
        );

        refreshFailed = true;
      }

      // Clear selected file without clearing the result.
      clearFile({ preserveMessage: true });

      // ---------------------------------------------------
      // SHOW IMPORT RESULT
      // ---------------------------------------------------

      setMessage({
        type: refreshFailed ? 'warning' : type,
        text: refreshFailed
          ? `${resultText} However, the application could not refresh its data.`
          : resultText,
      });
    } catch (error) {
      console.error('Feedback import error:', error);

      setMessage({
        type: 'error',
        text:
          error.message ||
          'Something went wrong during import. Please try again.',
      });
    } finally {
      setImporting(false);
    }
  };

  // -------------------------------------------------------
  // NOTIFICATION ICON
  // -------------------------------------------------------

  const NotificationIcon = () => {
    if (message?.type === 'success') {
      return (
        <CheckCircle2
          size={16}
          className="mt-0.5 shrink-0"
        />
      );
    }

    return (
      <AlertCircle
        size={16}
        className="mt-0.5 shrink-0"
      />
    );
  };

  // -------------------------------------------------------
  // NOTIFICATION STYLING
  // -------------------------------------------------------

  const notificationClasses = {
    success:
      'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300',

    warning:
      'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300',

    error:
      'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300',
  };

  // -------------------------------------------------------
  // RENDER
  // -------------------------------------------------------

  return (
    <div className="space-y-6">

      {/* PAGE DESCRIPTION */}

      <div>
        <p className="text-sm text-navy-500">
          Import customer feedback from CSV or JSON.
          Files are parsed in your browser. When you click
          Import, validated feedback records are sent to
          your account and saved by the backend.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">

        {/* UPLOAD SECTION */}

        <div className="space-y-6 lg:col-span-2">

          {/* DROP ZONE */}

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (
                event.key === 'Enter' ||
                event.key === ' '
              ) {
                event.preventDefault();
                inputRef.current?.click();
              }
            }}
            role="button"
            tabIndex={0}
            aria-label="Upload feedback file"
            className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
              dragging
                ? 'border-accent bg-indigo-50 dark:bg-indigo-500/10'
                : 'border-slate-300 bg-white hover:border-accent/60 dark:border-navy-700 dark:bg-navy-800'
            }`}
          >
            <UploadCloud
              size={36}
              className="mx-auto text-accent"
            />

            <p className="mt-3 text-sm font-medium">
              Drag and drop a file here, or{' '}
              <span className="text-accent">browse</span>
            </p>

            <p className="mt-1 text-xs text-navy-500">
              .csv or .json · max {formatBytes(MAX_FILE_BYTES)}
            </p>

            <input
              ref={inputRef}
              type="file"
              accept=".csv,.json,text/csv,application/json"
              className="hidden"
              onChange={(event) =>
                handleFile(event.target.files?.[0])
              }
            />
          </div>

          {/* SELECTED FILE */}

          {file && (
            <div className="card p-4">

              <div className="flex items-center gap-3">

                <div className="rounded-lg bg-indigo-50 p-2 text-accent dark:bg-indigo-500/15">
                  <FileText size={18} />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {file.name}
                  </p>

                  <p className="text-xs text-navy-500">
                    {formatBytes(file.size)}
                    {parsed &&
                      !parsed.fatal &&
                      ` · ${parsed.rows.length} rows detected`}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={clearFile}
                  className="btn-ghost p-1.5"
                  aria-label="Remove file"
                  disabled={importing}
                >
                  <X size={16} />
                </button>

              </div>

              {/* PARSING PROGRESS */}

              {(parsing || progress > 0) && (
                <div className="mt-3">

                  <div
                    className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-navy-700"
                    role="progressbar"
                    aria-valuenow={progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-200"
                      style={{
                        width: `${progress}%`,
                      }}
                    />
                  </div>

                  <p className="mt-1 text-xs text-navy-500">
                    {parsing ? 'Parsing file…' : 'Ready'}
                  </p>

                </div>
              )}

            </div>
          )}

          {/* IMPORT NOTIFICATION */}

          {message && (
            <div
              role={
                message.type === 'error'
                  ? 'alert'
                  : 'status'
              }
              className={`flex items-start gap-2 rounded-lg border p-3 text-sm ${
                notificationClasses[message.type] ||
                notificationClasses.error
              }`}
            >
              <NotificationIcon />

              <span>{message.text}</span>
            </div>
          )}

          {/* FILE PREVIEW */}

          {parsed && !parsed.fatal && (
            <div className="card overflow-hidden">

              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-navy-700">

                <div>
                  <h2 className="text-sm font-semibold">
                    Preview
                  </h2>

                  <p className="text-xs text-navy-500">
                    Showing {previewRows.length} of{' '}
                    {parsed.rows.length}.{' '}
                    {validRows.length} valid ·{' '}
                    {invalidRows.length} invalid
                  </p>
                </div>

                <Button
                  onClick={onImport}
                  loading={importing}
                  disabled={
                    !validRows.length ||
                    importing ||
                    parsing
                  }
                >
                  {importing
                    ? 'Importing...'
                    : `Import ${validRows.length} record(s)`}
                </Button>

              </div>

              {/* PREVIEW TABLE */}

              <div className="overflow-x-auto">

                <table className="min-w-full text-sm">

                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-navy-500 dark:bg-navy-900/40">
                    <tr>
                      <th className="px-4 py-2">Row</th>
                      <th className="px-4 py-2">Title</th>
                      <th className="px-4 py-2">Customer</th>
                      <th className="px-4 py-2">Sentiment</th>
                      <th className="px-4 py-2">Theme</th>
                      <th className="px-4 py-2">Votes</th>
                      <th className="px-4 py-2">Status</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100 dark:divide-navy-700">

                    {previewRows.map((row) => (
                      <tr key={row.rowNumber}>

                        <td className="px-4 py-2 text-navy-500">
                          {row.rowNumber}
                        </td>

                        <td className="max-w-[200px] truncate px-4 py-2">
                          {row.record.title || '—'}
                        </td>

                        <td className="px-4 py-2">
                          {row.record.customer}
                        </td>

                        <td className="px-4 py-2">
                          <Badge tone={row.record.sentiment}>
                            {row.record.sentiment}
                          </Badge>
                        </td>

                        <td className="px-4 py-2">
                          {row.record.theme}
                        </td>

                        <td className="px-4 py-2 tabular-nums">
                          {row.record.votes}
                        </td>

                        <td className="px-4 py-2">
                          {row.errors.length > 0 ? (
                            <span className="text-xs text-rose-600">
                              {row.errors.join(', ')}
                            </span>
                          ) : (
                            <span className="text-xs text-emerald-600">
                              OK
                            </span>
                          )}
                        </td>

                      </tr>
                    ))}

                  </tbody>

                </table>

              </div>

            </div>
          )}

          {/* EXPECTED FILE FORMAT */}

          <div className="card p-5 text-sm">

            <h2 className="mb-2 font-semibold">
              Expected fields
            </h2>

            <p className="text-navy-500">
              Required:{' '}
              <code className="rounded bg-slate-100 px-1 dark:bg-navy-700">
                raw_text
              </code>{' '}
              or{' '}
              <code className="rounded bg-slate-100 px-1 dark:bg-navy-700">
                message
              </code>
              .

              Optional:{' '}
              <code>
                feedback_id, title, source_channel, timestamp,
                customer, sentiment, theme, votes
              </code>
              .

              Missing optional fields get sensible defaults.
            </p>

            <p className="mt-2 text-navy-500">
              JSON accepts an array of objects or{' '}
              <code>{'{ "feedback": [ ... ] }'}</code>.
            </p>

          </div>

        </div>

        {/* UPLOAD HISTORY */}

        <div className="card h-fit p-5">

          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <History size={16} />
            Upload history
          </div>

          {history.length === 0 ? (
            <p className="text-sm text-navy-500">
              No uploads yet this session.
            </p>
          ) : (
            <ul className="space-y-3">

              {history.map((item) => (
                <li
                  key={item.id}
                  className="rounded-lg border border-slate-200 p-3 text-sm dark:border-navy-700"
                >

                  <p className="truncate font-medium">
                    {item.fileName}
                  </p>

                  <p className="text-xs text-navy-500">
                    {formatDateTime(item.at)} ·{' '}
                    {formatBytes(item.size)}
                  </p>

                  <p className="mt-1 text-xs">

                    <span className="text-emerald-600">
                      +{item.added} added
                    </span>

                    {item.skipped > 0 && (
                      <span className="text-amber-600">
                        {' '}· {item.skipped} skipped
                      </span>
                    )}

                    {item.invalid > 0 && (
                      <span className="text-rose-600">
                        {' '}· {item.invalid} invalid
                      </span>
                    )}

                  </p>

                  {item.importId && (
                    <p className="mt-1 break-all text-xs text-navy-500">
                      Import ID: {item.importId}
                    </p>
                  )}

                </li>
              ))}

            </ul>
          )}

          <Link
            to="/feedback"
            className="mt-4 inline-block text-sm font-medium text-accent"
          >
            View feedback list →
          </Link>

        </div>

      </div>

    </div>
  );
}
