"use client";

import { useCallback, useRef, useState } from "react";
import { uploadDocument, type Document } from "@/lib/api";

interface Props {
  onUploaded: (doc: Document) => void;
}

type DropState = "idle" | "dragging" | "uploading" | "error";

export default function DropZone({ onUploaded }: Props) {
  const [state, setState] = useState<DropState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (file.type !== "application/pdf") {
        setErrorMsg("Only PDF files are accepted.");
        setState("error");
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        setErrorMsg("File must be under 20 MB.");
        setState("error");
        return;
      }

      setState("uploading");
      setErrorMsg("");
      try {
        const doc = await uploadDocument(file);
        onUploaded(doc);
        setState("idle");
      } catch (err: unknown) {
        setErrorMsg(err instanceof Error ? err.message : "Upload failed.");
        setState("error");
      }
    },
    [onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setState("idle");
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  const borderColor =
    state === "dragging"
      ? "border-blue-500 bg-blue-50"
      : state === "error"
      ? "border-red-400 bg-red-50"
      : "border-gray-300 bg-gray-50 hover:bg-gray-100";

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setState("dragging");
      }}
      onDragLeave={() => setState("idle")}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 cursor-pointer transition-colors ${borderColor}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={onInputChange}
      />

      {state === "uploading" ? (
        <>
          <svg className="h-8 w-8 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <p className="text-sm text-gray-500">Uploading…</p>
        </>
      ) : (
        <>
          <svg className="h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 16v-8m0 0-3 3m3-3 3 3M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1" />
          </svg>
          <p className="text-sm font-medium text-gray-700">
            Drag & drop a PDF here, or <span className="text-blue-600">browse</span>
          </p>
          <p className="text-xs text-gray-400">PDF only · max 20 MB</p>
        </>
      )}

      {state === "error" && (
        <p className="text-sm text-red-600">{errorMsg}</p>
      )}
    </div>
  );
}
