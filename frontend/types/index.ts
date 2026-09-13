export interface SessionOut {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SourceOut {
  chunk_id: string;
  episode_title: string;
  guest: string | null;
  url: string | null;
  excerpt: string;
  score: number;
}

export interface MessageOut {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model: string | null;
  provider: string | null;
  sources: SourceOut[];
  created_at: string;
}

export interface ArtifactOut {
  id: string;
  session_id: string;
  message_id: string | null;
  type: "markdown" | "html";
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface SendMessageResponse {
  user_message: MessageOut;
  assistant_message: MessageOut;
  sources: SourceOut[];
  artifact: ArtifactOut | null;
  intent: string;
}

export interface ModelInfo {
  provider: "ollama" | "anthropic" | "openai";
  model: string;
  is_active: boolean;
  is_healthy: boolean;
  detail: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Record<string, unknown>;
  };
}

export class ApiError extends Error {
  code: string;
  requestId: string;
  status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.code = body.error.code;
    this.requestId = body.error.request_id;
    this.status = status;
  }
}
