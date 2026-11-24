import { useEffect, useMemo, useState } from 'react';

import {

  Plus,

  Search,

  Download,

  FileDown,

  Save,

  Pencil,

  FileText,

  Wand2,

  Trash2,

  X,

  AlertTriangle,

} from 'lucide-react';


import { apiClient } from '../api/apiClient';

import { useAppData } from '../context/AppDataContext';

import {

  generatePrdContent,

  contentToMarkdown,

  contentToText,

  SECTION_KEYS,

  SECTION_TITLES,

  normalizePrdContent,

} from '../utils/prdGenerator';

import { formatDate } from '../utils/formatters';


import Badge from '../components/common/Badge';

import Button from '../components/common/Button';

import Modal from '../components/common/Modal';

import EmptyState from '../components/common/EmptyState';


const PRD_STATUSES = ['Draft', 'In Review', 'Approved', 'Archived'];


const STATUS_TONE = {

  Draft: 'neutral',

  'In Review': 'accent',

  Approved: 'low',

  Archived: 'neutral',

};


/**

 * Convert strings, arrays and nested objects into readable PRD text.

 * The original content is not modified by this formatter.

 */

function formatPrdValue(value, depth = 0) {

  if (value === null || value === undefined || value === '') {

    return 'Not specified';

  }


  if (

    typeof value === 'string' ||

    typeof value === 'number' ||

    typeof value === 'boolean'

  ) {

    return String(value);

  }


  if (Array.isArray(value)) {

    if (value.length === 0) return 'None specified';


    return value

      .map((item) => {

        const formatted = formatPrdValue(item, depth + 1);

        return `${'  '.repeat(depth)}• ${formatted.replace(

          /\n/g,

          `\n${'  '.repeat(depth + 1)}`,

        )}`;

      })

      .join('\n');

  }


  if (typeof value === 'object') {

    const entries = Object.entries(value);

    if (entries.length === 0) return 'None specified';


    return entries

      .map(([key, nestedValue]) => {

        const label = key

          .replace(/([A-Z])/g, ' $1')

          .replace(/[\_-]/g, ' ')

          .replace(/^./, (character) => character.toUpperCase());


        return `${'  '.repeat(depth)}${label}:\n${formatPrdValue(

          nestedValue,

          depth + 1,

        )}`;

      })

      .join('\n\n');

  }


  return String(value);

}


/**

 * Read generated stories from either the PRD document or the persisted

 * artifact wrapper. Backend payloads may use snake_case or camelCase.

 */

const PRD_WRAPPER_KEYS = [
  'content',
  'document',
  'prd',
  'artifact',
  'data',
  'result',
  'output',
];

function unwrapPrdPayload(value) {
  let current = value;
  const visited = new Set();

  for (let depth = 0; depth < 8; depth += 1) {
    if (!current || typeof current !== 'object' || Array.isArray(current)) break;
    if (visited.has(current)) break;
    visited.add(current);

    const hasPrdSections = [
      'executive_summary',
      'executiveSummary',
      'problem_statement',
      'problemStatement',
      'functional_requirements',
      'functionalRequirements',
      'non_functional_requirements',
      'nonFunctionalRequirements',
      'success_metrics',
      'successMetrics',
      'user_stories',
      'userStories',
    ].some((key) => Object.prototype.hasOwnProperty.call(current, key));

    if (hasPrdSections) return current;

    const next = PRD_WRAPPER_KEYS
      .map((key) => current[key])
      .find((candidate) => candidate && typeof candidate === 'object');

    if (!next) break;
    current = next;
  }

  return current && typeof current === 'object' ? current : {};
}

function getUserStories(...sources) {
  const queue = [...sources];
  const visited = new Set();

  while (queue.length > 0) {
    const source = queue.shift();
    if (!source || typeof source !== 'object' || visited.has(source)) continue;
    visited.add(source);

    let stories = source.userStories ?? source.user_stories ?? source.stories;

    if (stories && !Array.isArray(stories) && typeof stories === 'object') {
      stories = stories.userStories ?? stories.user_stories ?? stories.stories;
    }

    if (Array.isArray(stories) && stories.length > 0) return stories;

    PRD_WRAPPER_KEYS.forEach((key) => {
      const nested = source[key];
      if (nested && typeof nested === 'object') queue.push(nested);
    });
  }

  return [];
}

function hasMeaningfulValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (typeof value === 'number' || typeof value === 'boolean') return true;
  if (Array.isArray(value)) return value.some(hasMeaningfulValue);
  if (typeof value === 'object') {
    return Object.values(value).some(hasMeaningfulValue);
  }
  return Boolean(value);
}

function getStoryAcceptanceCriteria(story) {

  const criteria =

    story?.acceptanceCriteria ??

    story?.acceptance_criteria ??

    story?.criteria ??

    [];


  return Array.isArray(criteria) ? criteria : [];

}


function formatAcceptanceCriteria(stories) {

  return stories.flatMap((story, storyIndex) => {

    const title =

      story.title ||

      story.story_title ||

      story.storyTitle ||

      `User Story ${storyIndex + 1}`;


    const storyText =

      story.userStory ||

      story.user_story ||

      story.description ||

      '';


    return getStoryAcceptanceCriteria(story).map((criterion, criterionIndex) => {

      if (typeof criterion === 'string') {

        return {

          story: title,

          criterion: `AC-${criterionIndex + 1}`,

          given: criterion,

          when: '',

          then: '',

        };

      }


      return {

        story: title,

        criterion:

          criterion.criterionId ||

          criterion.criterion_id ||

          `AC-${criterionIndex + 1}`,

        given: criterion.given || '',

        when: criterion.when || '',

        then: criterion.then || '',

        storyText,

      };

    });

  });

}


function formatUserStories(stories) {

  return stories.map((story, index) => ({

    id: story.storyId || story.story_id || `US-${index + 1}`,

    title: story.title || story.story_title || `User Story ${index + 1}`,

    userType: story.userType || story.user_type || '',

    userStory: story.userStory || story.user_story || story.description || '',

    priority: story.priority || '',

    requirementIds:

      story.requirementIds || story.requirement_ids || [],

    sourceFeedbackIds:

      story.sourceFeedbackIds || story.source_feedback_ids || [],

    acceptanceCriteria: getStoryAcceptanceCriteria(story),

    dependencies: story.dependencies || [],

  }));

}


function getRenderablePrdContent(prd) {
  const stored = prd?.content || {};
  const document = unwrapPrdPayload(stored);

  // Normalize backend snake_case fields while preserving unknown/custom sections.
  const normalized = normalizePrdContent(document);
  const stories = getUserStories(stored, prd, document);

  if (stories.length > 0) {
    normalized.userStories = formatUserStories(stories);
    normalized.acceptanceCriteria = formatAcceptanceCriteria(stories);
  }

  return normalized;
}

/**

 * Serialize structured values for editing without losing their data types.

 */

function getEditablePrdValue(value) {

  if (value === null || value === undefined) return '';

  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);

}


/**

 * If the original field was an object/array, attempt to parse the edited JSON.

 * If the user intentionally replaces it with prose, retain that prose as text.

 */

function parseEditedPrdValue(editedValue, originalValue) {

  if (typeof originalValue === 'object' && originalValue !== null) {

    try {

      return JSON.parse(editedValue);

    } catch {

      return editedValue;

    }

  }


  return editedValue;

}


export default function PRDViewer() {

  const { raw, loading, error, refresh } = useAppData();


  const [selectedId, setSelectedId] = useState(null);

  const [search, setSearch] = useState('');

  const [creating, setCreating] = useState(false);

  const [toast, setToast] = useState(null);

  const [prdToDelete, setPrdToDelete] = useState(null);

  const [deleting, setDeleting] = useState(false);


  useEffect(() => {

    refresh();

  }, [refresh]);


  const allPrds = Array.isArray(raw?.prds) ? raw.prds : [];

  const features = Array.isArray(raw?.features) ? raw.features : [];

  const feedback = Array.isArray(raw?.feedback) ? raw.feedback : [];

  const themes = Array.isArray(raw?.themes) ? raw.themes : [];


  const prds = useMemo(() => {

    const query = search.trim().toLowerCase();


    return allPrds.filter((prd) => {

      const feature = features.find((item) => item.id === prd.featureId);

      const title = (prd.title || '').toLowerCase();

      const featureName = (feature?.name || '').toLowerCase();


      return !query || title.includes(query) || featureName.includes(query);

    });

  }, [allPrds, features, search]);


  const selected =

    allPrds.find((prd) => prd.id === selectedId) || prds[0] || null;


  const featureFor = (id) => features.find((feature) => feature.id === id);


  const unlinkedFeatures = features.filter(

    (feature) => !allPrds.some((prd) => prd.featureId === feature.id),

  );


  const showToast = (type, text) => {

    setToast({ type, text });

  };


  const onSave = async (prdId, patch) => {

    const response = await apiClient.prds.update(prdId, patch);


    if (!response?.success) {

      showToast('error', response?.message || 'Could not save the PRD.');

      return false;

    }


    await refresh();

    showToast('success', 'PRD saved.');

    return true;

  };


  const confirmDelete = async () => {

    if (!prdToDelete?.id || deleting) return;


    setDeleting(true);


    try {

      const response = await apiClient.prds.remove(prdToDelete.id);


      if (!response?.success) {

        showToast('error', response?.message || 'Could not delete the PRD.');

        return;

      }


      const deletedId = prdToDelete.id;

      const remainingPrds = allPrds.filter((prd) => prd.id !== deletedId);

      const nextPrd = remainingPrds[0] || null;


      setSelectedId(nextPrd?.id || null);

      setPrdToDelete(null);


      await refresh();

      showToast('success', `"${prdToDelete.title}" was deleted.`);

    } catch (deleteError) {

      showToast(

        'error',

        deleteError?.message || 'An unexpected error occurred while deleting.',

      );

    } finally {

      setDeleting(false);

    }

  };


  if (loading) {

    return <div className="card h-64 animate-pulse" aria-label="Loading PRDs" />;

  }


  if (error) {

    return (

      <EmptyState

        title="Could not load PRDs"

        description={error}

      />

    );

  }


  if (!raw) return null;


  return (

    <>

      <style>{`

        @page {

          size: A4;

          margin: 18mm 16mm;

        }


        @media print {

          html,

          body,

          #root {

            width: 100% !important;

            height: auto !important;

            min-height: 0 !important;

            overflow: visible !important;

            background: #fff !important;

          }


          body * {

            visibility: hidden !important;

          }


          #prd-print-root,

          #prd-print-root * {

            visibility: visible !important;

          }


          #prd-print-root {

            position: absolute !important;

            inset: 0 auto auto 0 !important;

            width: 100% !important;

            max-width: none !important;

            margin: 0 !important;

            padding: 0 !important;

            border: 0 !important;

            border-radius: 0 !important;

            box-shadow: none !important;

            overflow: visible !important;

            background: #fff !important;

            color: #111827 !important;

          }


          #prd-print-root article {

            display: block !important;

            width: 100% !important;

            max-width: none !important;

            margin: 0 !important;

            padding: 0 !important;

            overflow: visible !important;

            color: #111827 !important;

          }


          #prd-print-root h1 {

            margin: 0 0 8mm !important;

            color: #111827 !important;

            font-size: 22pt !important;

            line-height: 1.2 !important;

            break-after: avoid-page !important;

          }


          #prd-print-root section {

            display: block !important;

            margin: 0 0 7mm !important;

            break-inside: auto !important;

            page-break-inside: auto !important;

          }


          #prd-print-root section h2 {

            margin: 0 0 3mm !important;

            padding: 0 0 2mm !important;

            color: #111827 !important;

            font-size: 12pt !important;

            line-height: 1.3 !important;

            break-after: avoid-page !important;

            border-color: #d1d5db !important;

          }


          #prd-print-root section > div {

            color: #1f2937 !important;

            font-size: 10pt !important;

            line-height: 1.55 !important;

            overflow-wrap: anywhere !important;

            white-space: pre-wrap !important;

          }


          #prd-print-root button,

          #prd-print-root select,

          #prd-print-root textarea,

          #prd-print-root .print\\:hidden {

            display: none !important;

          }


          #prd-print-root .card {

            border: 0 !important;

            box-shadow: none !important;

            overflow: visible !important;

          }


          a {

            color: inherit !important;

            text-decoration: none !important;

          }


          * {

            -webkit-print-color-adjust: exact !important;

            print-color-adjust: exact !important;

          }

        }

      `}</style>

      <div className="space-y-4">

      {toast && (

        <div

          role={toast.type === 'error' ? 'alert' : 'status'}

          className={`flex items-center justify-between gap-3 rounded-lg border p-3 text-sm ${

            toast.type === 'error'

              ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300'

              : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300'

          }`}

        >

          <span>{toast.text}</span>

          <button

            type="button"

            onClick={() => setToast(null)}

            className="shrink-0 text-xs underline"

          >

            Dismiss

          </button>

        </div>

      )}


      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">

        {/* PRD list */}

        <div className="card flex flex-col overflow-hidden">

          <div className="space-y-3 border-b border-slate-200 p-4 dark:border-navy-700">

            <div className="relative">

              <Search

                size={15}

                className="absolute left-3 top-1/2 -translate-y-1/2 text-navy-500"

              />

              <input

                value={search}

                onChange={(event) => setSearch(event.target.value)}

                placeholder="Search documents"

                className="input pl-9"

                aria-label="Search PRDs"

              />

            </div>


            <Button

              className="w-full"

              onClick={() => setCreating(true)}

              disabled={unlinkedFeatures.length === 0}

            >

              <Plus size={16} />

              {unlinkedFeatures.length

                ? 'Create PRD from feature'

                : 'All features have PRDs'}

            </Button>

          </div>


          {prds.length === 0 ? (

            <EmptyState

              icon={FileText}

              title={allPrds.length ? 'No matching PRDs' : 'No PRDs yet'}

              description={

                allPrds.length

                  ? 'Try another search term.'

                  : 'Create one from a prioritized feature.'

              }

            />

          ) : (

            <ul className="max-h-[70vh] divide-y divide-slate-100 overflow-y-auto dark:divide-navy-700">

              {prds.map((prd) => {

                const feature = featureFor(prd.featureId);

                const active = selected?.id === prd.id;

                const isBeingDeleted = deleting && prdToDelete?.id === prd.id;


                return (

                  <li

                    key={prd.id}

                    className={`flex items-stretch gap-1 px-2 ${

                      active

                        ? 'bg-indigo-50 dark:bg-indigo-500/10'

                        : 'hover:bg-slate-50 dark:hover:bg-navy-700/50'

                    }`}

                  >

                    <button

                      type="button"

                      onClick={() => setSelectedId(prd.id)}

                      className="min-w-0 flex-1 px-2 py-3 text-left transition"

                      aria-current={active ? 'page' : undefined}

                    >

                      <div className="flex items-start justify-between gap-2">

                        <p className="truncate text-sm font-medium">

                          {prd.title || 'Untitled PRD'}

                        </p>

                        <Badge tone={STATUS_TONE[prd.status] || 'neutral'}>

                          {prd.status || 'Draft'}

                        </Badge>

                      </div>


                      <p className="mt-0.5 truncate text-xs text-navy-500">

                        {feature?.name || 'Unlinked feature'}

                      </p>

                      <p className="mt-1 text-[11px] text-navy-500">

                        v{prd.version || '0.1'} · Updated{' '}

                        {formatDate(prd.updatedAt)}

                      </p>

                    </button>


                    <button

                      type="button"

                      onClick={() => setPrdToDelete(prd)}

                      disabled={deleting}

                      title={`Delete ${prd.title || 'PRD'}`}

                      aria-label={`Delete ${prd.title || 'PRD'}`}

                      className="my-2 inline-flex w-9 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-rose-950/30"

                    >

                      {isBeingDeleted ? (

                        <span className="text-xs">...</span>

                      ) : (

                        <Trash2 size={16} />

                      )}

                    </button>

                  </li>

                );

              })}

            </ul>

          )}

        </div>


        {/* PRD viewer */}

        {selected ? (

          <PRDDocument

            key={selected.id}

            prd={selected}

            feature={featureFor(selected.featureId)}

            feedback={feedback}

            themes={themes}

            onSave={onSave}

            onRequestDelete={() => setPrdToDelete(selected)}

          />

        ) : (

          <div className="card">

            <EmptyState

              icon={FileText}

              title="Select a PRD"

              description="Choose a document on the left to read or edit it."

            />

          </div>

        )}

      </div>


      {creating && (

        <CreatePrdModal

          features={unlinkedFeatures}

          feedback={feedback}

          themes={themes}

          onClose={() => setCreating(false)}

          onCreated={async (prd) => {

            setCreating(false);

            await refresh();

            setSelectedId(prd.id);

            showToast(

              'success',

              'PRD generated from template. You can edit it below.',

            );

          }}

        />

      )}


      {prdToDelete && (

        <Modal

          open

          onClose={() => {

            if (!deleting) setPrdToDelete(null);

          }}

          title="Delete PRD?"

          footer={

            <>

              <Button

                variant="outline"

                onClick={() => setPrdToDelete(null)}

                disabled={deleting}

              >

                Cancel

              </Button>

              <Button

                onClick={confirmDelete}

                loading={deleting}

                disabled={deleting}

              >

                <Trash2 size={15} />

                Delete permanently

              </Button>

            </>

          }

        >

          <div className="flex items-start gap-3">

            <div className="rounded-full bg-rose-100 p-2 text-rose-600 dark:bg-rose-950/40 dark:text-rose-300">

              <AlertTriangle size={20} />

            </div>

            <div className="min-w-0">

              <p className="text-sm font-medium text-navy-900 dark:text-white">

                You are about to delete “{prdToDelete.title || 'Untitled PRD'}”.

              </p>

              <p className="mt-1 text-sm text-navy-500">

                This permanently removes the PRD from your account. This action

                cannot be undone.

              </p>

            </div>

          </div>

        </Modal>

      )}

      </div>

    </>

  );

}


function PRDDocument({

  prd,

  feature,

  feedback,

  onSave,

  onRequestDelete,

}) {

  const [editing, setEditing] = useState(false);

  const [draft, setDraft] = useState(prd.content || {});

  const [status, setStatus] = useState(prd.status || 'Draft');

  const [saving, setSaving] = useState(false);


  const content = prd.content

    ? getRenderablePrdContent(prd)

    : generatePrdContent({

        feature: feature || { name: prd.title, theme: 'General' },

        feedbackForTheme: feedback.filter(

          (item) => item.theme === feature?.theme,

        ),

        rice: null,

      });


  const exportName = (prd.title || 'product-requirements')

    .replace(/[^a-z0-9]+/gi, '-')

    .toLowerCase();


  const download = (text, extension, mimeType) => {

    const blob = new Blob([text], { type: mimeType });

    const url = URL.createObjectURL(blob);

    const anchor = document.createElement('a');


    anchor.href = url;

    anchor.download = `${exportName}.${extension}`;

    anchor.click();


    URL.revokeObjectURL(url);

  };


  const startEditing = () => {

    setDraft(

      Object.fromEntries(

        Object.entries(content || {}).map(([key, value]) => [

          key,

          getEditablePrdValue(value),

        ]),

      ),

    );

    setEditing(true);

  };


  const save = async () => {

    setSaving(true);


    try {

      const updatedContent = Object.fromEntries(

        Object.entries(draft).map(([key, value]) => [

          key,

          parseEditedPrdValue(value, content?.[key]),

        ]),

      );


      const saved = await onSave(prd.id, {

        content: updatedContent,

        status,

      });


      if (saved) setEditing(false);

    } finally {

      setSaving(false);

    }

  };


  const changeStatus = async (nextStatus) => {

    const previousStatus = status;

    setStatus(nextStatus);


    const saved = await onSave(prd.id, { status: nextStatus });


    if (!saved) setStatus(previousStatus);

  };


  const sectionKeys = [

    ...new Set([...SECTION_KEYS, ...Object.keys(content || {})]),

  ];


  return (

    <div id="prd-print-root" className="card overflow-hidden print:shadow-none">

      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 p-5 dark:border-navy-700 print:hidden">

        <div className="min-w-0">

          <h2 className="truncate text-lg font-semibold">{prd.title}</h2>

          <p className="text-xs text-navy-500">

            Feature: {feature?.name || '—'} · Version {prd.version || '0.1'} ·

            Created {formatDate(prd.createdAt)} · Updated{' '}

            {formatDate(prd.updatedAt)}

          </p>

        </div>


        <div className="flex flex-wrap items-center gap-2">

          <select

            value={status}

            onChange={(event) => changeStatus(event.target.value)}

            className="input w-auto py-1.5 text-xs"

            aria-label="Document status"

            disabled={saving}

          >

            {PRD_STATUSES.map((item) => (

              <option key={item} value={item}>

                {item}

              </option>

            ))}

          </select>


          {editing ? (

            <>

              <Button

                onClick={save}

                loading={saving}

                disabled={saving}

              >

                <Save size={15} />

                Save changes

              </Button>

              <Button

                variant="outline"

                onClick={() => {

                  setEditing(false);

                  setDraft(prd.content || {});

                }}

                disabled={saving}

              >

                <X size={15} />

                Cancel

              </Button>

            </>

          ) : (

            <Button variant="outline" onClick={startEditing}>

              <Pencil size={15} />

              Edit

            </Button>

          )}


          <Button

            variant="outline"

            onClick={() =>

              download(

                contentToMarkdown(prd.title, content),

                'md',

                'text/markdown',

              )

            }

          >

            <Download size={15} />

            .md

          </Button>


          <Button

            variant="outline"

            onClick={() =>

              download(contentToText(prd.title, content), 'txt', 'text/plain')

            }

          >

            <Download size={15} />

            .txt

          </Button>


          <Button variant="outline" onClick={() => window.print()}>

            <FileDown size={15} />

            Export PDF

          </Button>


          <Button

            variant="outline"

            onClick={onRequestDelete}

            disabled={saving}

          >

            <Trash2 size={15} />

            Delete

          </Button>

        </div>

      </div>


      <article className="prose-doc mx-auto max-w-3xl space-y-8 p-6 sm:p-10">

        <h1 className="text-2xl font-semibold">{prd.title}</h1>


        {sectionKeys.map((key) => {
          if (!editing && !hasMeaningfulValue(content?.[key])) return null;

          return (
          <section key={key}>

            <h2 className="mb-2 border-b border-slate-200 pb-1.5 text-base font-semibold dark:border-navy-700">

              {SECTION_TITLES[key] ||

                key

                  .replace(/([A-Z])/g, ' $1')

                  .replace(/[\_-]/g, ' ')

                  .replace(/^./, (character) => character.toUpperCase())}

            </h2>


            {editing ? (

              <textarea

                aria-label={SECTION_TITLES[key] || key}

                rows={Math.max(

                  4,

                  String(draft[key] ?? '').split('\n').length + 1,

                )}

                value={draft[key] ?? getEditablePrdValue(content[key])}

                onChange={(event) =>

                  setDraft((current) => ({

                    ...current,

                    [key]: event.target.value,

                  }))

                }

                className="input w-full font-mono text-xs leading-relaxed"

              />

            ) : (

              <div className="whitespace-pre-line text-sm leading-relaxed text-navy-700 dark:text-slate-300">

                {formatPrdValue(content[key])}

              </div>

            )}

          </section>
          );
        })}
        {!editing && !sectionKeys.some((key) => hasMeaningfulValue(content?.[key])) && (
          <p className="text-sm text-navy-500">
            This PRD does not contain any populated sections yet.
          </p>
        )}
      </article>

    </div>

  );

}


function CreatePrdModal({

  features,

  feedback,

  themes,

  onClose,

  onCreated,

}) {

  const [featureId, setFeatureId] = useState(features[0]?.id || '');

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState('');


  const create = async () => {

    const feature = features.find((item) => item.id === featureId);


    if (!feature) {

      setError('Select a feature.');

      return;

    }


    setBusy(true);

    setError('');


    try {

      const theme = themes.find((item) => item.name === feature.theme);

      const linkedFeedback = feedback.filter(

        (item) => item.theme === feature.theme,

      );

      const content = generatePrdContent({

        feature,

        feedbackForTheme: linkedFeedback,

        rice: null,

      });


      const response = await apiClient.prds.create({

        title: `PRD: ${feature.name}`,

        featureId: feature.id,

        version: '0.1',

        status: 'Draft',

        content,

        themeId: theme?.id || null,

      });


      if (response?.success) {

        onCreated(response.data);

      } else {

        setError(response?.message || 'Could not create the PRD.');

      }

    } catch (createError) {

      setError(createError?.message || 'An unexpected error occurred.');

    } finally {

      setBusy(false);

    }

  };


  return (

    <Modal

      open

      onClose={onClose}

      title="Create PRD from feature"

      footer={

        <>

          <Button variant="outline" onClick={onClose} disabled={busy}>

            Cancel

          </Button>

          <Button onClick={create} loading={busy} disabled={busy}>

            <Wand2 size={15} />

            Generate PRD

          </Button>

        </>

      }

    >

      <p className="text-sm text-navy-500">

        Generates a draft from a local template using the feature&apos;s

        details and linked feedback. No AI model is called.

      </p>


      <label

        htmlFor="prd-feature"

        className="mt-4 block text-sm font-medium"

      >

        Feature

      </label>

      <select

        id="prd-feature"

        value={featureId}

        onChange={(event) => setFeatureId(event.target.value)}

        className="input mt-1.5"

        disabled={busy}

      >

        {features.map((feature) => (

          <option key={feature.id} value={feature.id}>

            {feature.name}

          </option>

        ))}

      </select>


      {error && (

        <p role="alert" className="mt-3 text-sm text-rose-600">

          {error}

        </p>

      )}

    </Modal>

  );

}
