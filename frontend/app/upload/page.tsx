"use client";

import { useState, useCallback } from "react";
import DropZone from "@/components/upload/DropZone";
import DocumentList from "@/components/upload/DocumentList";
import { type Document } from "@/lib/api";

export default function UploadPage() {
  const [uploaded, setUploaded] = useState<Document[]>([]);

  const handleUploaded = useCallback((doc: Document) => {
    setUploaded((prev) => [doc, ...prev]);
  }, []);

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-12 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Upload a PDF</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload a PDF document to start asking questions about it.
        </p>
      </div>

      <DropZone onUploaded={handleUploaded} />

      {uploaded.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-gray-700">Uploaded this session</h2>
          <DocumentList documents={uploaded} />
        </section>
      )}
    </main>
  );
}
