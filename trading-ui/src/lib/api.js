const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 15000;

export const API_BASE = (import.meta.env.VITE_API_URL || DEFAULT_API_BASE).replace(/\/+$/, "");
export const BASE_URL = API_BASE;

export class ApiError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status ?? null;
    this.code = options.code ?? null;
    this.payload = options.payload ?? null;
    this.isConnectionError = Boolean(options.isConnectionError);
  }
}

function isFormDataBody(body) {
  return typeof FormData !== "undefined" && body instanceof FormData;
}

function mergeSignals(timeoutMs, externalSignal) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => clearTimeout(timeoutId),
  };
}

async function parseResponse(res) {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return await res.json();
  }

  const text = await res.text();
  return text ? { message: text } : {};
}

function buildHeaders(headers, body) {
  const nextHeaders = new Headers(headers || {});
  if (!isFormDataBody(body) && !nextHeaders.has("Content-Type")) {
    nextHeaders.set("Content-Type", "application/json");
  }
  return nextHeaders;
}

export async function apiFetch(path, options = {}) {
  const {
    timeout = DEFAULT_TIMEOUT_MS,
    headers,
    body,
    signal,
    ...rest
  } = options;

  const requestBody = isFormDataBody(body)
    ? body
    : body !== undefined && body !== null && typeof body !== "string"
      ? JSON.stringify(body)
      : body;

  const { signal: mergedSignal, cleanup } = mergeSignals(timeout, signal);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: buildHeaders(headers, body),
      body: requestBody,
      signal: mergedSignal,
    });

    const payload = await parseResponse(res);
    if (!res.ok) {
      const message =
        payload?.error ||
        payload?.detail ||
        payload?.message ||
        (res.status >= 500 ? "Server error" : "Request failed");
      throw new ApiError(message, { status: res.status, payload });
    }

    return payload;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    const isAbort = error?.name === "AbortError";
    const message = isAbort ? "Server unavailable" : "Server unavailable";
    throw new ApiError(message, {
      code: isAbort ? "TIMEOUT" : "NETWORK_ERROR",
      isConnectionError: true,
    });
  } finally {
    cleanup();
  }
}

export function apiGet(path, options = {}) {
  return apiFetch(path, { ...options, method: "GET" });
}

export function apiPost(path, body, options = {}) {
  return apiFetch(path, { ...options, method: "POST", body });
}

export function apiPostForm(path, formData, options = {}) {
  return apiFetch(path, { ...options, method: "POST", body: formData });
}

export function isServerUnavailableError(error) {
  return Boolean(error?.isConnectionError || error?.code === "NETWORK_ERROR" || error?.code === "TIMEOUT");
}

export function getApiErrorMessage(error, fallback = "Server error") {
  if (isServerUnavailableError(error)) {
    return "Server unavailable";
  }

  if (typeof error?.message === "string" && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

export function getConnectivityMessage() {
  return "Server connection lost. Please ensure the backend server is running.";
}

export function buildApiErrorState(error, fallbackTitle, fallbackDescription) {
  if (isServerUnavailableError(error)) {
    return {
      title: "Server connection lost",
      description: "Start backend server and retry.",
    };
  }

  return {
    title: fallbackTitle,
    description: getApiErrorMessage(error, fallbackDescription),
  };
}

export function extractErrorMessage(error) {
  return getApiErrorMessage(error, "Unknown error");
}

export const api = {
  get: apiGet,
  post: apiPost,
  postForm: apiPostForm,
  ping: () => apiGet("/health"),
};
