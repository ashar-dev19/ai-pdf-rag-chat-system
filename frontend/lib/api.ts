const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Provider = "gemini" | "voyage_claude";

export interface Document {
  id: string;
  filename: string;
  file_size: number;
  page_count: number;
  storage_path: string;
  status: "processing" | "ready" | "failed";
  provider: Provider;
  created_at: string;
}

export interface SourceCitation {
  filename: string;
  document_id: string;
  chunk_index: number;
  excerpt: string;
  score: number;
}

export interface UsageInfo {
  input_tokens: number;
  output_tokens: number;
  model: string;
}

export interface ModelUsage {
  model: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_requests: number;
  today_requests: number;
  last_minute_requests: number;
}

export interface UsageResponse {
  models: ModelUsage[];
}

export async function getOverallUsage(): Promise<UsageResponse> {
  const res = await fetch(`${API_BASE}/api/v1/usage/`, { cache: "no-store" });
  const data = await res.json();
  if (!res.ok) return { models: [] };
  return data as UsageResponse;
}

export async function getDocumentUsage(documentId: string): Promise<UsageResponse> {
  const res = await fetch(`${API_BASE}/api/v1/usage/${documentId}`, { cache: "no-store" });
  const data = await res.json();
  if (!res.ok) return { models: [] };
  return data as UsageResponse;
}

export interface ChatResponse {
  query: string;
  answer: string;
  sources: SourceCitation[];
  usage?: UsageInfo;
}

export async function uploadDocument(file: File, provider: Provider = "gemini"): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("provider", provider);

  const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: "POST",
    body: form,
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "Upload failed");
  return data as Document;
}

export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/api/v1/documents/`, { cache: "no-store" });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "Failed to fetch documents");
  return data as Document[];
}

export async function getDocument(id: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, { cache: "no-store" });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "Document not found");
  return data as Document;
}

export async function chatDocument(
  query: string,
  documentId: string,
  provider: Provider = "gemini",
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/v1/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, document_id: documentId, provider }),
  });

  const data = await res.json();
  if (!res.ok) {
    const err = new Error(data.detail ?? "Chat failed") as Error & { retryAfter?: number };
    if (res.status === 429 || res.status === 503) {
      const retryAfter = res.headers.get("Retry-After");
      if (retryAfter) err.retryAfter = parseInt(retryAfter);
    }
    throw err;
  }
  return data as ChatResponse;
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "Delete failed");
  }
}

export async function deleteAllDocuments(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/documents/`, { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "Delete all failed");
  }
}

export async function* chatStream(
  query: string,
  documentId: string,
  provider: Provider = "gemini",
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, document_id: documentId, provider }),
  });

  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => ({}));
    const retryAfter = res.headers.get("Retry-After");
    const msg = data.detail ?? "Stream failed";
    const err = new Error(msg) as Error & { retryAfter?: number };
    if (res.status === 429 && retryAfter) err.retryAfter = parseInt(retryAfter);
    throw err;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const payload = part.slice(6);
      if (payload === "[DONE]") return;
      if (payload === "[ERROR]") throw new Error("Stream error");
      // Rate limit signal from stream: [RATE_LIMIT:seconds]
      const rlMatch = payload.match(/^\[RATE_LIMIT:(\d+)\]$/);
      if (rlMatch) {
        const err = new Error(`Rate limit reached. Please wait ${rlMatch[1]} seconds before trying again.`) as Error & { retryAfter?: number };
        err.retryAfter = parseInt(rlMatch[1]);
        throw err;
      }
      yield payload.replace(/\\n/g, "\n");
    }
  }
}
