// Rule-based local assistant. Answers are built from the CURRENT shared data passed in,
// not from a fixed script. No external AI API is called.
import { analyzeThemes } from '../utils/themeAnalyzer';
import { computeRice } from '../utils/riceScore';
import { generatePrdContent } from '../utils/prdGenerator';

const pct = (n, d) => (d ? Math.round((n / d) * 100) : 0);

const summarizeFeedback = (d) => {
  const f = d.feedback;
  if (!f.length) return 'There is no feedback yet. Upload a CSV or JSON file to get started.';
  const neg = f.filter((x) => x.sentiment === 'negative').length;
  const pos = f.filter((x) => x.sentiment === 'positive').length;
  const top = [...f].sort((a, b) => b.votes - a.votes).slice(0, 3);
  const customers = new Set(f.map((x) => x.customer)).size;
  return [
    `Across ${f.length} feedback records from ${customers} customers, ${pct(neg, f.length)}% are negative and ${pct(pos, f.length)}% are positive.`,
    `The most-voted items are: ${top.map((t) => `"${t.title}" (${t.votes} votes)`).join('; ')}.`,
  ].join(' ');
};

const complaints = (d) => {
  const neg = d.feedback.filter((x) => x.sentiment === 'negative');
  if (!neg.length) return 'There are no negative feedback records right now, so no complaint patterns to report.';
  const stats = analyzeThemes(d.feedback, d.themes).filter((t) => t.count > 0);
  const worst = stats.filter((t) => t.negative > 0).sort((a, b) => b.negative - a.negative).slice(0, 3);
  return `Most complaints (${neg.length} negative records) cluster around: ${worst.map((t) => `${t.name} (${t.negative})`).join(', ')}.`;
};

const prioritizeNext = (d) => {
  const scored = d.features.map((f) => ({ ...f, rice: computeRice(f).score })).filter((f) => !computeRice(f).error);
  if (!scored.length) return 'No features are scored yet. Add features on the Prioritization page to get a recommendation.';
  const candidates = scored.filter((f) => f.status !== 'Completed').sort((a, b) => b.rice - a.rice);
  const top = candidates[0];
  if (!top) return 'All scored features are already completed.';
  return `Based on RICE, "${top.name}" scores highest at ${top.rice.toLocaleString()} (reach ${top.reach.toLocaleString()}, impact ${top.impact}, confidence ${Math.round(top.confidence * 100)}%, effort ${top.effort}). Its status is "${top.status}".`;
};

const topThemes = (d) => {
  const stats = analyzeThemes(d.feedback, d.themes).filter((t) => t.count > 0);
  if (!stats.length) return 'No themes have feedback yet. Upload feedback, then run Analyze Themes.';
  return `Highest-priority themes right now: ${stats.slice(0, 3).map((t) => `${t.name} (score ${t.priorityScore}, ${t.count} items)`).join('; ')}.`;
};

const roadmapSummary = (d) => {
  const r = d.roadmap;
  if (!r.length) return 'The roadmap is empty. Add items on the Roadmap page.';
  const byStatus = ['Planned', 'In Progress', 'In Review', 'Completed'].map((s) => `${r.filter((x) => x.status === s).length} ${s.toLowerCase()}`).join(', ');
  const overdue = r.filter((x) => x.status !== 'Completed' && new Date(x.targetDate) < new Date());
  const next = r.filter((x) => x.status !== 'Completed').sort((a, b) => new Date(a.targetDate) - new Date(b.targetDate))[0];
  return [
    `The roadmap has ${r.length} items: ${byStatus}.`,
    overdue.length ? `${overdue.length} item(s) are overdue: ${overdue.map((o) => o.name).join(', ')}.` : 'Nothing is overdue.',
    next ? `The next target is "${next.name}" on ${new Date(next.targetDate).toLocaleDateString()}, owned by ${next.owner}.` : '',
  ].filter(Boolean).join(' ');
};

const generatePrdReply = (d, text) => {
  const lower = text.toLowerCase();
  const feature = d.features.find((f) => lower.includes(f.name.toLowerCase())) || d.features[0];
  if (!feature) return 'There are no features to write a PRD for yet. Add one on the Prioritization page first.';
  const linked = d.feedback.filter((f) => f.theme === feature.theme);
  const content = generatePrdContent({ feature, feedbackForTheme: linked, rice: computeRice(feature).score });
  return `Here is a draft PRD outline for "${feature.name}" (local template, ${linked.length} linked feedback records):\n\n**Problem:** ${content.problemStatement.split('\n')[0]}\n**Success metrics:** ${content.successMetrics.split('\n')[0].replace(/^- /, '')}.\n\nOpen the PRD Viewer to create the full document and edit it.`;
};

const helpText = 'I can answer questions about feedback, complaints, theme priorities, RICE-based feature priorities, the roadmap, and PRD drafts. Try the suggested prompts.';

// Routes the question to the most relevant handler. Ordering matters: specific intents first.
export const answer = (question, data) => {
  const q = question.toLowerCase();
  if (!data) return 'Data is still loading. Please try again in a moment.';
  if (/\b(prd|requirements? doc|spec)\b/.test(q)) return generatePrdReply(data, question);
  if (/\b(roadmap|milestone|timeline|release)\b/.test(q)) return roadmapSummary(data);
  if (/\b(prioriti[sz]e|next feature|rice|which feature|should we build)\b/.test(q)) return prioritizeNext(data);
  if (/\b(theme|themes)\b/.test(q)) return topThemes(data);
  if (/\b(complain|complaint|problem|issue|pain)/.test(q)) return complaints(data);
  if (/\b(summar|feedback|recent|customer|sentiment)\b/.test(q)) return summarizeFeedback(data);
  return helpText;
};

export const SUGGESTED_PROMPTS = [
  'Summarize recent feedback',
  'What are the most common complaints?',
  'Which feature should we prioritize next?',
  'What are our highest-priority themes?',
  'Generate a PRD for a selected feature',
  'Summarize the roadmap',
];
