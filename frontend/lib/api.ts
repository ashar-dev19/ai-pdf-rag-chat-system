const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Document {
  id: string;
  filename: string;
  file_size: number;
  page_count: number;
  storage_path: string;
  status: "processing" | "ready" | "failed";
  created_at: string;
}

export async function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);

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
