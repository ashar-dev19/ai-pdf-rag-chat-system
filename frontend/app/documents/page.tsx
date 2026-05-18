"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import DropZone from "@/components/upload/DropZone";
import { listDocuments, deleteDocument, deleteAllDocuments, getOverallUsage, type Document, type ModelUsage } from "@/lib/api";
import UsageStats from "@/components/usage/UsageStats";

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const STATUS_STYLES: Record<Document["status"], string> = {
  processing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-600",
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [deletingAll, setDeletingAll] = useState(false);
  const [usageModels, setUsageModels] = useState<ModelUsage[]>([]);

  const fetchDocuments = useCallback(async () => {
    try {
      const [docs, usage] = await Promise.all([listDocuments(), getOverallUsage()]);
      setDocuments(docs);
      setUsageModels(usage.models);
    } catch {
      setError("Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUploaded = useCallback((doc: Document) => {
    setDocuments((prev) => [doc, ...prev]);
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    if (!confirm("Delete this document? This will remove the file and all its vectors.")) return;
    setDeletingIds((prev) => new Set([...prev, id]));
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      setError("Failed to delete document.");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, []);

  const handleDeleteAll = useCallback(async () => {
    if (!confirm("Delete ALL documents? This removes every file and all vectors. This cannot be undone.")) return;
    setDeletingAll(true);
    setError("");
    try {
      await deleteAllDocuments();
      setDocuments([]);
    } catch {
      setError("Failed to delete all documents.");
    } finally {
      setDeletingAll(false);
    }
  }, []);

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-10 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Documents</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload a PDF then click Chat to ask questions about it.
        </p>
      </div>

      <DropZone onUploaded={handleUploaded} />

      <UsageStats models={usageModels} title="Overall Model Usage" />

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-gray-600 uppercase tracking-wide">
            Your documents
          </h2>
          {documents.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={deletingAll}
              className="text-xs font-medium text-red-500 hover:text-red-700 disabled:opacity-50 transition-colors"
            >
              {deletingAll ? "Deleting all…" : "Delete all"}
            </button>
          )}
        </div>

        {loading && (
          <p className="text-sm text-gray-400">Loading…</p>
        )}

        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}

        {!loading && !error && documents.length === 0 && (
          <p className="rounded-lg border border-dashed border-gray-200 p-8 text-center text-sm text-gray-400">
            No documents yet. Upload a PDF above to get started.
          </p>
        )}

        {documents.length > 0 && (
          <ul className="flex flex-col gap-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="truncate text-sm font-medium text-gray-800">
                    {doc.filename}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formatBytes(doc.file_size)} · {doc.page_count} page{doc.page_count !== 1 ? "s" : ""}
                  </span>
                </div>

                <div className="ml-4 flex shrink-0 items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    doc.provider === "voyage_claude"
                      ? "bg-purple-100 text-purple-700"
                      : "bg-gray-100 text-gray-600"
                  }`}>
                    {doc.provider === "voyage_claude" ? "Claude" : "Gemini"}
                  </span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[doc.status]}`}>
                    {doc.status}
                  </span>
                  {doc.status === "ready" && (
                    <Link
                      href={`/chat/${doc.id}`}
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 transition-colors"
                    >
                      Chat
                    </Link>
                  )}
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingIds.has(doc.id)}
                    className="rounded-md p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-40 transition-colors"
                    title="Delete document"
                  >
                    {deletingIds.has(doc.id) ? (
                      <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                      </svg>
                    )}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
