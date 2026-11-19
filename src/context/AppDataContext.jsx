
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "./AuthContext";
import { apiClient, isMockMode } from "../api/apiClient";

import {
  analyzeThemes,
  sentimentCounts,
} from "../utils/themeAnalyzer";

import {
  computeRice,
  priorityFromScore,
} from "../utils/riceScore";


const AppDataContext = createContext(null);


// ---------------------------------------------------------
// APPLICATION DATA PROVIDER
// ---------------------------------------------------------

export function AppDataProvider({ children }) {

  const {
    user,
    isLoading: authLoading,
  } = useAuth();

  const [state, setState] = useState({
    loading: true,
    error: null,
    data: null,
  });

  // Separate state for persisted AI analysis.
  const [analysis, setAnalysis] = useState({
    loading: true,
    running: false,
    error: null,
    latest: null,
    runs: [],
  });


  // -------------------------------------------------------
  // LOAD EXISTING APPLICATION DATA
  // -------------------------------------------------------

  const refresh = useCallback(async () => {

    const res = await apiClient.loadState();

    if (res.success) {

      setState({
        loading: false,
        error: null,
        data: res.data,
      });

    } else {

      setState({
        loading: false,
        error: res.message,
        data: null,
      });

    }

    return res;

  }, []);


  // -------------------------------------------------------
  // LOAD SAVED AI ANALYSIS
  // -------------------------------------------------------

  const refreshAnalysis = useCallback(async () => {

    if (!user) {
      return {
        success: false,
        message: "User is not authenticated.",
      };
    }

    if (
      typeof apiClient.analysis?.getLatest !== "function" ||
      typeof apiClient.analysis?.getRuns !== "function"
    ) {

      setAnalysis({
        loading: false,
        running: false,
        error: isMockMode
          ? "AI analysis requires real API mode."
          : "Analysis API is unavailable.",
        latest: null,
        runs: [],
      });

      return {
        success: false,
        message: "Analysis API is unavailable.",
      };
    }

    setAnalysis((previous) => ({
      ...previous,
      loading: true,
      error: null,
    }));

    try {

      const [latestResponse, historyResponse] =
        await Promise.all([
          apiClient.analysis.getLatest(),
          apiClient.analysis.getRuns(null, 20),
        ]);

      // An empty history is valid. The latest endpoint
      // may return 404 when no analysis has been saved.
      const latest = latestResponse.success
        ? latestResponse.data
        : null;

      const runs = historyResponse.success
        ? historyResponse.data?.items || []
        : [];

      const error = historyResponse.success
        ? null
        : historyResponse.message;

      setAnalysis((previous) => ({
        ...previous,
        loading: false,
        error,
        latest,
        runs,
      }));

      return {
        success: historyResponse.success,
        latest,
        runs,
        message: error,
      };

    } catch (error) {

      const message =
        error.message || "Could not retrieve AI analysis.";

      setAnalysis((previous) => ({
        ...previous,
        loading: false,
        error: message,
      }));

      return {
        success: false,
        message,
      };
    }

  }, [user]);


  // -------------------------------------------------------
  // RUN ALL FOUR AI AGENTS
  // -------------------------------------------------------

  const runAnalysis = useCallback(async (workspaceId = null) => {

    if (!user) {
      return {
        success: false,
        message: "Please log in before running AI analysis.",
      };
    }

    if (typeof apiClient.analysis?.run !== "function") {
      return {
        success: false,
        message: "AI analysis is unavailable in the current API mode.",
      };
    }

    setAnalysis((previous) => ({
      ...previous,
      running: true,
      error: null,
    }));

    try {

      const response = await apiClient.analysis.run(
        workspaceId
      );

      if (!response.success) {

        setAnalysis((previous) => ({
          ...previous,
          running: false,
          error: response.message,
        }));

        return response;
      }

      // The POST endpoint returns the saved MongoDB document.
      const savedRun = response.data;

      // Refresh the run history after successful persistence.
      const historyResponse =
        await apiClient.analysis.getRuns(null, 20);

      setAnalysis((previous) => ({
        ...previous,
        running: false,
        loading: false,
        error: historyResponse.success
          ? null
          : "Analysis was saved, but history could not be refreshed.",
        latest: savedRun,
        runs: historyResponse.success
          ? historyResponse.data?.items || []
          : previous.runs,
      }));

      return response;

    } catch (error) {

      const message =
        error.message || "AI analysis could not be completed.";

      setAnalysis((previous) => ({
        ...previous,
        running: false,
        error: message,
      }));

      return {
        success: false,
        message,
      };
    }

  }, [user]);


  // -------------------------------------------------------
  // RETRIEVE A PARTICULAR ANALYSIS RUN
  // -------------------------------------------------------

  const getAnalysisRun = useCallback(async (runId) => {

    if (typeof apiClient.analysis?.getById !== "function") {
      return {
        success: false,
        message: "Analysis retrieval is unavailable.",
      };
    }

    return apiClient.analysis.getById(runId);

  }, []);


  // -------------------------------------------------------
  // LOAD DATA AFTER AUTHENTICATION RESTORATION
  // -------------------------------------------------------

  useEffect(() => {

    // Don't fetch data until authentication is restored.
    if (authLoading) {
      return;
    }

    if (!user) {

      setState({
        loading: false,
        error: null,
        data: null,
      });

      setAnalysis({
        loading: false,
        running: false,
        error: null,
        latest: null,
        runs: [],
      });

      return;
    }

    refresh();
    refreshAnalysis();

  }, [
    user,
    authLoading,
    refresh,
    refreshAnalysis,
  ]);


  // -------------------------------------------------------
  // DERIVED APPLICATION DATA
  // -------------------------------------------------------

  const derived = useMemo(() => {

    const d = state.data;

    if (!d) return null;

    const feedback = d.feedback || [];
    const themes = d.themes || [];
    const features = d.features || [];
    const prds = d.prds || [];

    const themeStats = analyzeThemes(
      feedback,
      themes
    );

    const scored = features.map((feature) => {

      const { score, error } = computeRice(feature);

      return {
        ...feature,
        rice: score,
        riceError: error,
      };
    });

    const allScores = scored.map(
      (feature) => feature.rice
    );

    const prioritized = scored
      .map((feature) => ({
        ...feature,
        priority: priorityFromScore(
          feature.rice,
          allScores
        ),
      }))
      .sort((a, b) => b.rice - a.rice);

    return {
      feedbackCount: feedback.length,

      activeThemes: themeStats.filter(
        (theme) => theme.count > 0
      ).length,

      prioritizedCount: prioritized.length,

      prdCount: prds.length,

      themeStats,

      prioritized,

      sentiment: sentimentCounts(feedback),
    };

  }, [state.data]);


  // -------------------------------------------------------
  // CONTEXT VALUE
  // -------------------------------------------------------

  const value = useMemo(() => ({

    // Existing application state.
    loading: state.loading,
    error: state.error,
    raw: state.data,
    derived,
    refresh,

    // New AI analysis state.
    analysis,

    // New AI analysis actions.
    runAnalysis,
    refreshAnalysis,
    getAnalysisRun,

  }), [
    state,
    derived,
    refresh,
    analysis,
    runAnalysis,
    refreshAnalysis,
    getAnalysisRun,
  ]);


  return (
    <AppDataContext.Provider value={value}>
      {children}
    </AppDataContext.Provider>
  );
}


// ---------------------------------------------------------
// CUSTOM HOOK
// ---------------------------------------------------------

export const useAppData = () => {

  const ctx = useContext(AppDataContext);

  if (!ctx) {
    throw new Error(
      "useAppData must be used inside AppDataProvider"
    );
  }

  return ctx;
};
