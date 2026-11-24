
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

const realRequest = async (method, url, body, requestConfig = {}) => {
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
// REAL API
// ---------------------------------------------------------

const realApi = {
  auth: {
    login: (email, password) =>
      realRequest("post", "/auth/login", { email, password }),

    register: (payload) =>
      realRequest("post", "/auth/register", payload),

    logout: () =>
      realRequest("post", "/auth/logout"),

    currentUser: () =>
      realRequest("get", "/auth/me"),
  },

  admin: {
    getUsers: () =>
      realRequest("get", "/admin/users"),

    updateRole: (userId, role) =>
      realRequest(
        "patch",
        `/admin/users/${encodeURIComponent(userId)}/role`,
        { role }
      ),

    updateStatus: (userId, isActive) =>
      realRequest(
        "patch",
        `/admin/users/${encodeURIComponent(userId)}/status`,
        { isActive }
      ),

    getAuditLogs: () =>
      realRequest("get", "/admin/audit-logs"),
  },

  loadState: () =>
    realRequest("get", "/state", undefined, {
      timeout: 30000,
    }),

  feedback: {
    getAll: () =>
      realRequest("get", "/feedback"),

    create: (data) =>
      realRequest("post", "/feedback", data),

    update: (id, data) =>
      realRequest(
        "put",
        `/feedback/${encodeURIComponent(id)}`,
        data
      ),

    remove: (id) =>
      realRequest(
        "delete",
        `/feedback/${encodeURIComponent(id)}`
      ),

    getDatasets: () =>
      realRequest("get", "/feedback/datasets"),

    importMany: (rows, fileName = "Uploaded dataset") =>
      realRequest("post", "/feedback/import", {
        records: rows,
        fileName,
      }),
  },

  workspaces: {
    getAll: () =>
      realRequest("get", "/workspaces"),

    create: (data) =>
      realRequest("post", "/workspaces", data),

    update: (id, data) =>
      realRequest(
        "put",
        `/workspaces/${encodeURIComponent(id)}`,
        data
      ),

    switchTo: (id) =>
      realRequest(
        "post",
        `/workspaces/${encodeURIComponent(id)}/switch`
      ),
  },

  themes: {
    getAll: () =>
      realRequest("get", "/themes"),

    saveKeywords: (id, keywords) =>
      realRequest(
        "put",
        `/themes/${encodeURIComponent(id)}/keywords`,
        { keywords }
      ),
  },

  prioritization: {
    getAll: () =>
      realRequest("get", "/features"),

    create: (data) =>
      realRequest("post", "/features", data),

    update: (id, data) =>
      realRequest(
        "put",
        `/features/${encodeURIComponent(id)}`,
        data
      ),

    remove: (id) =>
      realRequest(
        "delete",
        `/features/${encodeURIComponent(id)}`
      ),
  },

  prds: {
    getAll: () =>
      realRequest("get", "/prds"),

    create: (data) =>
      realRequest("post", "/prds", data),

    update: (id, data) =>
      realRequest(
        "put",
        `/prds/${encodeURIComponent(id)}`,
        data
      ),

    remove: (id) =>
      realRequest(
        "delete",
        `/prds/${encodeURIComponent(id)}`
      ),
  },

  roadmap: {
    getAll: () =>
      realRequest("get", "/roadmap"),

    create: (data) =>
      realRequest("post", "/roadmap", data),

    update: (id, data) =>
      realRequest(
        "put",
        `/roadmap/${encodeURIComponent(id)}`,
        data
      ),

    remove: (id) =>
      realRequest(
        "delete",
        `/roadmap/${encodeURIComponent(id)}`
      ),
  },

  dashboard: {
    getActivity: () =>
      realRequest("get", "/activity"),
  },

  // -------------------------------------------------------
  // ANALYSIS
  // Supports both imported and historical datasets.
  // -------------------------------------------------------

  analysis: {
    run: (workspaceId = null, datasetSelection = null) => {
      const payload = {
        ...(workspaceId !== null && workspaceId !== undefined
          ? { workspaceId }
          : {}),
      };

      // Backward compatibility: older callers can pass an import ID string.
      if (
        typeof datasetSelection === "string" &&
        datasetSelection.trim()
      ) {
        payload.importId = datasetSelection.trim();
      } else if (datasetSelection?.dataset_type === "legacy") {
        payload.datasetName = datasetSelection.dataset_name;
      } else if (
        datasetSelection?.dataset_type === "import" &&
        datasetSelection.import_id
      ) {
        payload.importId = datasetSelection.import_id;
      }

      return realRequest("post", "/analysis/run", payload, {
        timeout: 330000,
      });
    },

    getRuns: (workspaceId = null, limit = 20) =>
      realRequest("get", "/analysis/runs", undefined, {
        params: {
          ...(workspaceId ? { workspaceId } : {}),
          limit,
        },
      }),

    getLatest: (workspaceId = null) =>
      realRequest("get", "/analysis/runs/latest", undefined, {
        params: workspaceId ? { workspaceId } : {},
      }),

    getById: (runId) =>
      realRequest(
        "get",
        `/analysis/runs/${encodeURIComponent(runId)}`
      ),
  },

  preferences: {
    update: (data) =>
      realRequest("put", "/preferences", data),
  },

  // -------------------------------------------------------
  // CHAT
  // Conversations are individually addressed.
  // Never call clear() to create a new conversation.
  // -------------------------------------------------------

  chat: {
    sendMessage: (payload) =>
      realRequest("post", "/chat", payload, {
        timeout: 130000,
      }),

    getConversations: () =>
      realRequest("get", "/chat/conversations"),

    getConversation: (conversationId) =>
      realRequest(
        "get",
        `/chat/conversations/${encodeURIComponent(conversationId)}`
      ),

    saveConversation: (conversationId, payload) =>
      realRequest(
        "put",
        `/chat/conversations/${encodeURIComponent(conversationId)}`,
        payload,
        { timeout: 30000 }
      ),

    deleteConversation: (conversationId) =>
      realRequest(
        "delete",
        `/chat/conversations/${encodeURIComponent(conversationId)}`
      ),

    // Legacy endpoints retained for migration/compatibility only.
    getHistory: () =>
      realRequest("get", "/chat"),

    saveHistory: (messages) =>
      realRequest("put", "/chat", { messages }),

    // WARNING: deletes all chat history for the authenticated user.
    // Not used by New Chat.
    clear: () =>
      realRequest("delete", "/chat"),
  },
};

export const apiClient = apiConfig.isMock ? mockApi : realApi;
export const isMockMode = apiConfig.isMock;
