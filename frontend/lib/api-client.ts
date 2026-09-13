import {
  ApiError,
  ApiErrorBody,
  ArtifactOut,
  MessageOut,
  ModelInfo,
  SendMessageResponse,
  SessionOut,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });

  if (!resp.ok) {
    let body: ApiErrorBody;
    try {
      body = await resp.json();
    } catch {
      body = { error: { code: "UNKNOWN", message: resp.statusText, request_id: "unknown" } };
    }
    throw new ApiError(resp.status, body);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; detail: Record<string, string> }>("/health/ready"),

  createSession: (title?: string) =>
    request<SessionOut>("/api/sessions", { method: "POST", body: JSON.stringify({ title: title || "New chat" }) }),

  listSessions: () => request<SessionOut[]>("/api/sessions"),

  getSession: (id: string) => request<SessionOut>(`/api/sessions/${id}`),

  deleteSession: (id: string) => request<void>(`/api/sessions/${id}`, { method: "DELETE" }),

  listMessages: (sessionId: string) => request<MessageOut[]>(`/api/sessions/${sessionId}/messages`),

  listSessionArtifacts: (sessionId: string) =>
    request<ArtifactOut[]>(`/api/sessions/${sessionId}/artifacts`),

  sendMessage: (sessionId: string, content: string) =>
    request<SendMessageResponse>(`/api/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  generateShip30: (sessionId: string, topic: string) =>
    request<ArtifactOut>("/api/skills/ship30", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, topic }),
    }),

  createArtifact: (sessionId: string, requestText: string, type: "markdown" | "html") =>
    request<ArtifactOut>("/api/artifacts", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, request: requestText, type }),
    }),

  getArtifact: (id: string) => request<ArtifactOut>(`/api/artifacts/${id}`),

  listModels: () => request<ModelInfo[]>("/api/models"),

  selectModel: (provider: string) =>
    request<ModelInfo>("/api/models/select", { method: "POST", body: JSON.stringify({ provider }) }),

  sendFeedback: (messageId: string, rating: "up" | "down") =>
    request<void>("/api/feedback", { method: "POST", body: JSON.stringify({ message_id: messageId, rating }) }),
};

export { ApiError };
