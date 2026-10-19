// RICE = (Reach × Impact × Confidence) / Effort
// Confidence is a fraction in [0, 1]. Effort must be > 0 to avoid division by zero.
export const computeRice = ({ reach, impact, confidence, effort }) => {
  const r = Number(reach);
  const i = Number(impact);
  const c = Number(confidence);
  const e = Number(effort);
  if (![r, i, c, e].every(Number.isFinite)) return { score: 0, error: 'All RICE inputs must be numbers.' };
  if (r < 0) return { score: 0, error: 'Reach cannot be negative.' };
  if (c < 0 || c > 1) return { score: 0, error: 'Confidence must be between 0 and 1.' };
  if (e <= 0) return { score: 0, error: 'Effort must be greater than 0.' };
  return { score: Math.round((r * i * c) / e), error: null };
};

export const validateRiceInput = (f) => {
  const { score, error } = computeRice(f);
  return error;
};

// Priority buckets based on RICE score percentile within the current feature set.
export const priorityFromScore = (score, allScores) => {
  if (!allScores.length) return 'Low';
  const sorted = [...allScores].sort((a, b) => b - a);
  const rank = sorted.indexOf(score);
  const pct = rank / sorted.length;
  if (pct < 0.34) return 'High';
  if (pct < 0.67) return 'Medium';
  return 'Low';
};
