import { Capacitor } from "@capacitor/core";

import type {
  AuthResult,
  AuthTokens,
  Claim,
  ClaimPayload,
  ClaimReviewPayload,
  Conversation,
  CurrentUser,
  Item,
  LoginPayload,
  Notification,
  RegisterPayload
} from "./types";

const configuredApiUrl = import.meta.env.VITE_API_URL as string | undefined;
const API_URLS = [
  configuredApiUrl,
  ...(Capacitor.isNativePlatform()
    ? [
      "https://lost-and-found-murex-kappa.vercel.app/api",
      "http://127.0.0.1:8000/api",
      "http://10.0.2.2:8000/api",
      "http://10.10.6.122:8000/api",
      "http://192.168.1.54:8000/api"
    ]
    : ["/api"])
].filter((url, index, urls): url is string => Boolean(url) && urls.indexOf(url) === index);

let activeApiUrl = API_URLS[0];
const REQUEST_TIMEOUT_MS = 6000;

const ACCESS_KEY = "lostfound.access";
const REFRESH_KEY = "lostfound.refresh";

type RequestOptions = RequestInit & {
  retry?: boolean;
};

export function getStoredTokens(): AuthTokens | null {
  const access = localStorage.getItem(ACCESS_KEY);
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!access || !refresh) {
    return null;
  }
  return { access, refresh };
}

export function storeTokens(tokens: AuthTokens) {
  localStorage.setItem(ACCESS_KEY, tokens.access);
  localStorage.setItem(REFRESH_KEY, tokens.refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function isFormData(body: BodyInit | null | undefined): body is FormData {
  return typeof FormData !== "undefined" && body instanceof FormData;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string"
      ? payload
      : payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : JSON.stringify(payload);
    throw new Error(message || "Request failed");
  }

  return payload as T;
}

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getStoredTokens();
  if (!tokens?.refresh) {
    return null;
  }

  const response = await fetchApi("/auth/token/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh })
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const payload = await response.json() as { access: string };
  storeTokens({ access: payload.access, refresh: tokens.refresh });
  return payload.access;
}

function isRetryableNetworkError(error: unknown) {
  return error instanceof TypeError
    || (error instanceof DOMException && error.name === "AbortError");
}

async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const abortFromParent = () => controller.abort();

  if (options.signal?.aborted) {
    controller.abort();
  } else {
    options.signal?.addEventListener("abort", abortFromParent, { once: true });
  }

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal
    });
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abortFromParent);
  }
}

async function fetchApi(path: string, options: RequestInit): Promise<Response> {
  const apiUrls = [activeApiUrl, ...API_URLS.filter((url) => url !== activeApiUrl)];
  let lastError: unknown;

  for (const apiUrl of apiUrls) {
    try {
      const response = await fetchWithTimeout(`${apiUrl}${path}`, options);
      activeApiUrl = apiUrl;
      return response;
    } catch (error) {
      lastError = error;

      if (!isRetryableNetworkError(error)) {
        throw error;
      }
    }
  }

  throw lastError;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const tokens = getStoredTokens();
  const headers = new Headers(options.headers);
  const body = options.body;

  if (body && !isFormData(body) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (tokens?.access) {
    headers.set("Authorization", `Bearer ${tokens.access}`);
  }

  let response: Response;
  try {
    response = await fetchApi(path, {
      ...options,
      headers
    });
  } catch (error) {
    console.error("FETCH ERROR:", error);

    if (error instanceof TypeError) {
      throw new Error(
        `Fetch failed while calling the Django API at ${API_URLS.join(" or ")}. ` +
        "This can be caused by the API being unreachable, CORS, mixed content, Android cleartext HTTP blocking, stale native build settings, or the phone being on a different network segment. " +
        "For USB debugging, run adb reverse tcp:8000 tcp:8000. For Wi-Fi, use a LAN IP the phone can reach."
      );
    }
    throw error;
  }

  if (response.status === 401 && options.retry !== false && tokens?.refresh) {
    const access = await refreshAccessToken();
    if (access) {
      return request<T>(path, { ...options, retry: false });
    }
  }

  return parseResponse<T>(response);
}

export function login(payload: LoginPayload): Promise<AuthTokens> {
  return request<AuthTokens>("/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function register(payload: RegisterPayload): Promise<AuthResult> {
  return request<AuthResult>("/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/me/");
}

export type ItemQuery = {
  q?: string;
  status?: string;
  category?: string;
  report_type?: string;
};

export function listItems(query: ItemQuery = {}): Promise<Item[]> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<Item[]>(`/items/${suffix}`);
}

export function getItem(id: number): Promise<Item> {
  return request<Item>(`/items/${id}/`);
}

export function createItem(formData: FormData): Promise<Item> {
  return request<Item>("/items/", {
    method: "POST",
    body: formData
  });
}

export function submitClaim(itemId: number, payload: ClaimPayload): Promise<Claim> {
  return request<Claim>(`/items/${itemId}/claims/`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function reviewClaim(claimId: number, payload: ClaimReviewPayload): Promise<Claim> {
  return request<Claim>(`/claims/${claimId}/review/`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function startConversation(itemId: number): Promise<Conversation> {
  return request<Conversation>(`/items/${itemId}/start-conversation/`, {
    method: "POST"
  });
}

export function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/conversations/");
}

export function listNotifications(): Promise<Notification[]> {
  return request<Notification[]>("/notifications/");
}

export function markNotificationRead(id: number): Promise<Notification> {
  return request<Notification>(`/notifications/${id}/read/`, {
    method: "POST"
  });
}

export function markAllNotificationsRead(): Promise<{ updated: number }> {
  return request<{ updated: number }>("/notifications/read-all/", {
    method: "POST"
  });
}

export function getConversation(id: number): Promise<Conversation> {
  return request<Conversation>(`/conversations/${id}/`);
}

export function sendMessage(conversationId: number, body: string): Promise<void> {
  return request<void>(`/conversations/${conversationId}/messages/`, {
    method: "POST",
    body: JSON.stringify({ body })
  });
}
