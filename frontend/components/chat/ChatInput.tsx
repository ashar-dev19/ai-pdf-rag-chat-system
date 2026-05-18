"use client";

import { useRef, useState } from "react";

interface Props {
  onSend: (query: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const query = value.trim();
    if (!query || disabled) return;
    onSend(query);
    setValue("");
    textareaRef.current?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-sm focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-400 transition">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder="Ask a question about this document…"
        className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder-gray-400 outline-none disabled:opacity-50"
        style={{ maxHeight: "120px" }}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="shrink-0 rounded-lg bg-blue-600 p-1.5 text-white transition hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Send"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}
