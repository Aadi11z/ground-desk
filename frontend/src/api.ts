import type {
  ChatResponse,
  ClientConfig,
  DocumentRecord,
  Identity,
} from "./types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

type RequestOptions = {
  accessToken?: string;
  workspaceId?: string;
  init?: RequestInit;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { accessToken, workspaceId, init = {} } = options;
  const headers = new Headers(init.headers);
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  if (workspaceId) {
    headers.set("X-Workspace-ID", workspaceId);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(await responseMessage(response));
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

async function responseMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  return body.detail ?? `Request failed (${response.status}).`;
}

export function getClientConfig(): Promise<ClientConfig> {
  return request("/api/client-config");
}

export function getCurrentIdentity(accessToken: string): Promise<Identity> {
  return request("/api/me", { accessToken });
}

export function getDocuments(
  accessToken: string,
  workspaceId: string,
): Promise<DocumentRecord[]> {
  return request("/api/documents", { accessToken, workspaceId });
}

export function askQuestion(
  accessToken: string,
  workspaceId: string,
  question: string,
): Promise<ChatResponse> {
  return request("/api/chat", {
    accessToken,
    workspaceId,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
  });
}

export function uploadDocument(
  accessToken: string,
  workspaceId: string,
  file: File,
): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/documents", {
    accessToken,
    workspaceId,
    init: { method: "POST", body: form },
  });
}
