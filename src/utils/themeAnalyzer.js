// Local keyword-based theme analysis. Labelled "mock/local analysis" in the UI.
// Does not call any external AI service.
export const analyzeThemes = (feedback, themes) => {
  // Re-assign a theme only when the feedback has no explicit theme or it is "Uncategorized".
  const scored = feedback.map((f) => {
    if (f.theme && f.theme !== 'Uncategorized') return { ...f, matchedTheme: f.theme };
    const text = `${f.title} ${f.message}`.toLowerCase();
    let best = null;
    let bestHits = 0;
    themes.forEach((t) => {
      const hits = t.keywords.reduce((n, kw) => n + (text.includes(kw.toLowerCase()) ? 1 : 0), 0);
      if (hits > bestHits) { best = t.name; bestHits = hits; }
    });
    return { ...f, matchedTheme: best || 'Uncategorized' };
  });

  const stats = themes.map((t) => {
    const items = scored.filter((f) => f.matchedTheme === t.name);
    const count = items.length;
    const positive = items.filter((f) => f.sentiment === 'positive').length;
    const negative = items.filter((f) => f.sentiment === 'negative').length;
    const neutral = count - positive - negative;
    const totalVotes = items.reduce((s, f) => s + (f.votes || 0), 0);
    const negShare = count ? negative / count : 0;
    // Priority: volume × votes × negativity, normalized to 0–100 later.
    const raw = count * 2 + totalVotes * 0.5 + negShare * 20;
    return {
      id: t.id, name: t.name, description: t.description, keywords: t.keywords,
      count, positive, neutral, negative, totalVotes,
      negativeShare: Math.round(negShare * 100),
      rawPriority: raw,
      items,
    };
  });

  const maxRaw = Math.max(1, ...stats.map((s) => s.rawPriority));
  return stats
    .map((s) => ({ ...s, priorityScore: Math.round((s.rawPriority / maxRaw) * 100) }))
    .sort((a, b) => b.priorityScore - a.priorityScore);
};

export const sentimentCounts = (feedback) => ({
  positive: feedback.filter((f) => f.sentiment === 'positive').length,
  neutral: feedback.filter((f) => f.sentiment === 'neutral').length,
  negative: feedback.filter((f) => f.sentiment === 'negative').length,
});
