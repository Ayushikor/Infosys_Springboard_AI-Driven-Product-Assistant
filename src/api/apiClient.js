
import axios from "axios";
import { apiConfig } from "./apiConfig";
import { mockApi } from "./mockApi";

// ---------------------------------------------------------
// AXIOS CLIENT
// ---------------------------------------------------------

const http = axios.create({
  baseURL: apiConfig.baseUrl,
  timeout: 10000,
  withCredentials: true,
});

// ---------------------------------------------------------
// REQUEST HANDLER
// ---------------------------------------------------------

const realRequest = async (
  method,
  url,
  body,
  requestConfig = {}
) => {
  try {
    const response = await http.request({
      method,
      url,
      ...(body !== undefined ? { data: body } : {}),
      ...requestConfig,
    });

    return response.data;

  } catch (err) {
    const message = err.response
      ? err.response.data?.message ||
        `Server responded with ${err.response.status}`
      : `Cannot reach backend at ${apiConfig.baseUrl}. Is the server running?`;

    return {
      success: false,
      data: null,
      message,
    };
  }
};

// ---------------------------------------------------------
// UNIMPLEMENTED ENDPOINT HANDLER
// ---------------------------------------------------------

const notImplemented = (name) => () =>
  Promise.resolve({
    success: false,
    data: null,
    message: `${name} is not implemented on the backend yet.`,
  });

// ---------------------------------------------------------
// REAL API
// ---------------------------------------------------------

const realApi = {

  // -------------------------------------------------------
  // AUTHENTICATION
  // -------------------------------------------------------

  auth: {
    login: (email, password) =>
      realRequest("post", "/auth/login", {
        email,
        password,
      }),

    register: (payload) =>
      realRequest("post", "/auth/register", payload),

    logout: () =>
      realRequest("post", "/auth/logout"),

    currentUser: () =>
      realRequest("get", "/auth/me"),
  },

  // -------------------------------------------------------
  // APPLICATION STATE
  // -------------------------------------------------------

  loadState: () =>
    realRequest("get", "/state"),

  // -------------------------------------------------------
  // FEEDBACK
  // -------------------------------------------------------

  feedback: {

    getAll: () =>
      realRequest("get", "/feedback"),

    create: (data) =>
      realRequest("post", "/feedback", data),

    update: (id, data) =>
      realRequest("put", `/feedback/${id}`, data),

    remove: (id) =>
      realRequest("delete", `/feedback/${id}`),

    getDatasets: () =>
      realRequest("get", "/feedback/datasets"),

    importMany: (rows, fileName = "Uploaded dataset") =>
      realRequest("post", "/feedback/import", {
        records: rows,
        fileName,
      }),
  },

  // -------------------------------------------------------
  // WORKSPACES
  // -------------------------------------------------------

  workspaces: {
    getAll: () =>
      realRequest("get", "/workspaces"),

    create: (data) =>
      realRequest("post", "/workspaces", data),

    update: (id, data) =>
      realRequest("put", `/workspaces/${id}`, data),

    switchTo: (id) =>
      realRequest("post", `/workspaces/${id}/switch`),
  },

  // -------------------------------------------------------
  // THEMES
  // -------------------------------------------------------

  themes: {
  getAll: () => realRequest("get", "/themes"),
    saveKeywords: (id, keywords) =>
      realRequest("put", `/themes/${id}/keywords`, {
        keywords,
      }),
  },

  // -------------------------------------------------------
  // FEATURE PRIORITIZATION
  // -------------------------------------------------------

  prioritization: {
    getAll: () =>
      realRequest("get", "/features"),

    create: (data) =>
      realRequest("post", "/features", data),

    update: (id, data) =>
      realRequest("put", `/features/${id}`, data),

    remove: (id) =>
      realRequest("delete", `/features/${id}`),
  },

  // -------------------------------------------------------
  // PRODUCT REQUIREMENT DOCUMENTS
  // -------------------------------------------------------

  prds: {
    getAll: () =>
      realRequest("get", "/prds"),

    create: (data) =>
      realRequest("post", "/prds", data),

    update: (id, data) =>
      realRequest("put", `/prds/${id}`, data),

    remove: (id) =>
      realRequest("delete", `/prds/${id}`),
  },

  // -------------------------------------------------------
  // ROADMAP
  // -------------------------------------------------------

  roadmap: {
    getAll: () =>
      realRequest("get", "/roadmap"),

    create: (data) =>
      realRequest("post", "/roadmap", data),

    update: (id, data) =>
      realRequest("put", `/roadmap/${id}`, data),

    remove: (id) =>
      realRequest("delete", `/roadmap/${id}`),
  },

  // -------------------------------------------------------
  // DASHBOARD
  // -------------------------------------------------------

  dashboard: {
    getActivity: () =>
      realRequest("get", "/activity"),
  },

  // -------------------------------------------------------
  // AI ANALYSIS - FOUR AGENT PIPELINE
  // -------------------------------------------------------

  analysis: {

    run: (workspaceId = null, importId = null) =>
      realRequest(
        "post",
        "/analysis/run",
        {
          ...(workspaceId !== null && workspaceId !== undefined
            ? { workspaceId }
            : {}),

          ...(importId !== null && importId !== undefined
            ? { importId }
            : {}),
        },
        {
          timeout: 330000,
        }
      ),

    getRuns: (workspaceId = null, limit = 20) =>
      realRequest(
        "get",
        "/analysis/runs",
        undefined,
        {
          params: {
            ...(workspaceId ? { workspaceId } : {}),
            limit,
          },
        }
      ),

    getLatest: (workspaceId = null) =>
      realRequest(
        "get",
        "/analysis/runs/latest",
        undefined,
        {
          params: workspaceId
            ? { workspaceId }
            : {},
        }
      ),

    getById: (runId) =>
      realRequest(
        "get",
        `/analysis/runs/${encodeURIComponent(runId)}`
      ),
  },

  // -------------------------------------------------------
  // USER PREFERENCES
  // -------------------------------------------------------

  preferences: {
    update: (data) =>
      realRequest("put", "/preferences", data),
  },

  // -------------------------------------------------------
  // AI PRODUCT ASSISTANT CHAT
  // -------------------------------------------------------

  chat: {

    // Send a message to the unified AI chatbot.
    // Supports automatic intent detection and explicit
    // agent selection through the request payload.

    sendMessage: (payload) =>
      realRequest(
        "post",
        "/chat",
        payload,
        {
          timeout: 130000,
        }
      ),

    // Retrieve saved conversation history.

    getHistory: () =>
      realRequest("get", "/chat"),

    // Save conversation history.

    saveHistory: (messages) =>
      realRequest("put", "/chat", {
        messages,
      }),

    // Clear conversation history.

    clear: () =>
      realRequest("delete", "/chat"),
  },
};

// ---------------------------------------------------------
// EXPORT
// ---------------------------------------------------------

export const apiClient = apiConfig.isMock
  ? mockApi
  : realApi;

export const isMockMode = apiConfig.isMock;
