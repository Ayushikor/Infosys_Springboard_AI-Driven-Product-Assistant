
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
// INITIAL STATES
// ---------------------------------------------------------

const initialAppState = {
  loading: true,
  error: null,
  data: null,
};

const initialAnalysisState = {
  loading: true,
  running: false,
  error: null,
  latest: null,
  runs: [],

  // Uploaded dataset state.
  datasets: [],
  datasetsLoading: false,
  datasetsError: null,
};


// ---------------------------------------------------------
// NORMALIZE DATASET RESPONSE
// ---------------------------------------------------------

const normalizeDatasets = (responseData) => {

  const items = Array.isArray(responseData)
    ? responseData
    : Array.isArray(responseData?.items)
      ? responseData.items
      : Array.isArray(responseData?.datasets)
        ? responseData.datasets
        : [];

  return items
    .map((item) => {

      const importId =
        item.import_id ??
        item.importId ??
        null;

      return {
        ...item,

        import_id: importId,

        fileName:
          item.fileName ||
          item.file_name ||
          item.filename ||
          item.name ||
          "Uploaded dataset",

        recordCount:
          Number(
            item.recordCount ??
            item.record_count ??
            item.count ??
            0
          ),

        importedAt:
          item.importedAt ||
          item.imported_at ||
          item.createdAt ||
          null,
      };
    })
    .filter(
      (item) =>
        typeof item.import_id === "string" &&
        item.import_id.trim().length > 0
    );
};


// ---------------------------------------------------------
// APPLICATION DATA PROVIDER
// ---------------------------------------------------------

export function AppDataProvider({ children }) {

  const {
    user,
    isLoading: authLoading,
  } = useAuth();

  const [state, setState] = useState(initialAppState);

  const [analysis, setAnalysis] = useState(
    initialAnalysisState
  );


  // -------------------------------------------------------
  // LOAD EXISTING APPLICATION DATA
  // -------------------------------------------------------

  const refresh = useCallback(async () => {

    try {

      const response = await apiClient.loadState();

      if (response.success) {

        setState({
          loading: false,
          error: null,
          data: response.data,
        });

      } else {

        setState({
          loading: false,
          error: response.message || "Could not load application data.",
          data: null,
        });

      }

      return response;

    } catch (error) {

      const message =
        error.message || "Could not load application data.";

      setState({
        loading: false,
        error: message,
        data: null,
      });

      return {
        success: false,
        message,
      };
    }

  }, []);


  // -------------------------------------------------------
  // LOAD UPLOADED DATASETS
  // -------------------------------------------------------

  const refreshDatasets = useCallback(async () => {

    if (!user) {
      return {
        success: false,
        message: "User is not authenticated.",
      };
    }

    if (
      typeof apiClient.feedback?.getDatasets !== "function"
    ) {

      const message = isMockMode
        ? "Uploaded dataset selection requires real API mode."
        : "Dataset retrieval is unavailable.";

      setAnalysis((previous) => ({
        ...previous,
        datasetsLoading: false,
        datasetsError: message,
        datasets: [],
      }));

      return {
        success: false,
        message,
      };
    }

    setAnalysis((previous) => ({
      ...previous,
      datasetsLoading: true,
      datasetsError: null,
    }));

    try {

      const response =
        await apiClient.feedback.getDatasets();

      if (!response.success) {

        setAnalysis((previous) => ({
          ...previous,
          datasetsLoading: false,
          datasetsError:
            response.message || "Could not load uploaded datasets.",
        }));

        return response;
      }

      const datasets = normalizeDatasets(
        response.data
      );

      setAnalysis((previous) => ({
        ...previous,
        datasetsLoading: false,
        datasetsError: null,
        datasets,
      }));

      return {
        success: true,
        data: datasets,
      };

    } catch (error) {

      const message =
        error.message || "Could not load uploaded datasets.";

      setAnalysis((previous) => ({
        ...previous,
        datasetsLoading: false,
        datasetsError: message,
      }));

      return {
        success: false,
        message,
      };
    }

  }, [user]);


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

      const message = isMockMode
        ? "AI analysis requires real API mode."
        : "Analysis API is unavailable.";

      setAnalysis((previous) => ({
        ...previous,
        loading: false,
        running: false,
        error: message,
        latest: null,
        runs: [],
      }));

      return {
        success: false,
        message,
      };
    }

    setAnalysis((previous) => ({
      ...previous,
      loading: true,
      error: null,
    }));

    try {

      const [
        latestResponse,
        historyResponse,
      ] = await Promise.all([
        apiClient.analysis.getLatest(),
        apiClient.analysis.getRuns(null, 20),
      ]);

      // The latest endpoint may return 404 when no analysis
      // has been saved. An empty history is valid.
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

  const runAnalysis = useCallback(
    async (
      workspaceId = null,
      importId = null
    ) => {

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

      // Dataset-specific analysis requires a valid import ID.
      if (
        importId !== null &&
        (
          typeof importId !== "string" ||
          !importId.trim()
        )
      ) {
        return {
          success: false,
          message: "Please select a valid uploaded dataset.",
        };
      }

      setAnalysis((previous) => ({
        ...previous,
        running: true,
        error: null,
      }));

      try {

        const response = await apiClient.analysis.run(
          workspaceId,
          importId
        );

        if (!response.success) {

          setAnalysis((previous) => ({
            ...previous,
            running: false,
            error: response.message || "Analysis failed.",
          }));

          return response;
        }

        // The POST endpoint returns the saved MongoDB document.
        const savedRun = response.data;

        // Refresh history after successful persistence.
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

    },
    [user]
  );


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

    // Wait until authentication restoration is complete.
    if (authLoading) {
      return;
    }

    if (!user) {

      setState({
        ...initialAppState,
        loading: false,
      });

      setAnalysis({
        ...initialAnalysisState,
        loading: false,
      });

      return;
    }

    refresh();
    refreshAnalysis();
    refreshDatasets();

  }, [
    user,
    authLoading,
    refresh,
    refreshAnalysis,
    refreshDatasets,
  ]);


  // -------------------------------------------------------
  // DERIVED APPLICATION DATA
  // -------------------------------------------------------

  const derived = useMemo(() => {

    const d = state.data;

    if (!d) {
      return null;
    }

    const feedback = d.feedback || [];
    const themes = d.themes || [];
    const features = d.features || [];
    const prds = d.prds || [];

    const themeStats = analyzeThemes(
      feedback,
      themes
    );

    const scored = features.map((feature) => {

      const {
        score,
        error,
      } = computeRice(feature);

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
      .sort(
        (a, b) => b.rice - a.rice
      );

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

    // AI analysis state.
    analysis,

    // AI analysis actions.
    runAnalysis,
    refreshAnalysis,
    getAnalysisRun,

    // Dataset actions.
    refreshDatasets,

  }), [
    state,
    derived,
    refresh,
    analysis,
    runAnalysis,
    refreshAnalysis,
    getAnalysisRun,
    refreshDatasets,
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
