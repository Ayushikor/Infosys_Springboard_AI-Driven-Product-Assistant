import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from './AuthContext';
import { apiClient } from '../api/apiClient';
import { analyzeThemes, sentimentCounts } from '../utils/themeAnalyzer';
import { computeRice, priorityFromScore } from '../utils/riceScore';

const AppDataContext = createContext(null);

// Holds the current user's data. Every mutation calls the API, then refreshes here,
// so dashboard, themes, PRDs, and roadmap all read one source of truth.
export function AppDataProvider({ children }) {
  const { user } = useAuth();
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const refresh = useCallback(async () => {
    const res = await apiClient.loadState();
    if (res.success) setState({ loading: false, error: null, data: res.data });
    else setState({ loading: false, error: res.message, data: null });
    return res;
  }, []);

  useEffect(() => {
    if (user) refresh();
    else setState({ loading: false, error: null, data: null });
  }, [user, refresh]);

  // Derived values are computed from raw data so they can never drift from each other.
  const derived = useMemo(() => {
    const d = state.data;
    if (!d) return null;
    const themeStats = analyzeThemes(d.feedback, d.themes);
    const scored = d.features.map((f) => {
      const { score, error } = computeRice(f);
      return { ...f, rice: score, riceError: error };
    });
    const allScores = scored.map((f) => f.rice);
    const prioritized = scored
      .map((f) => ({ ...f, priority: priorityFromScore(f.rice, allScores) }))
      .sort((a, b) => b.rice - a.rice);
    return {
      feedbackCount: d.feedback.length,
      activeThemes: themeStats.filter((t) => t.count > 0).length,
      prioritizedCount: prioritized.length,
      prdCount: d.prds.length,
      themeStats,
      prioritized,
      sentiment: sentimentCounts(d.feedback),
    };
  }, [state.data]);

  const value = useMemo(() => ({
    loading: state.loading,
    error: state.error,
    raw: state.data,
    derived,
    refresh,
  }), [state, derived, refresh]);

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

export const useAppData = () => {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error('useAppData must be used inside AppDataProvider');
  return ctx;
};
