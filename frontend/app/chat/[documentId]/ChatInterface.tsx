"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ChatMessage, { type Message } from "@/components/chat/ChatMessage";
import ChatInput from "@/components/chat/ChatInput";
import { chatStream, chatDocument, getDocumentUsage, type SourceCitation, type Provider, type ModelUsage } from "@/lib/api";
import UsageStats from "@/components/usage/UsageStats";

interface Props {
  documentId: string;
  filename: string;
  provider: Provider;
}

export default function ChatInterface({ documentId, filename, provider }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [retryCountdown, setRetryCountdown] = useState(0);
  const [retryReason, setRetryReason] = useState<"rate_limit" | "overloaded">("rate_limit");
  const [usageModels, setUsageModels] = useState<ModelUsage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getDocumentUsage(documentId).then((u) => setUsageModels(u.models));
  }, [documentId]);

  // Countdown timer when rate-limited
  useEffect(() => {
    if (retryCountdown <= 0) return;
    const t = setTimeout(() => setRetryCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [retryCountdown]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(
    async (query: string) => {
      setError("");
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: query,
      };

      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStreaming(true);

      try {
        let fullText = "";
        let sources: SourceCitation[] = [];

        for await (const chunk of chatStream(query, documentId, provider)) {
          fullText += chunk;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: fullText } : m
            )
          );
        }

        const result = await chatDocument(query, documentId, provider);
        sources = result.sources;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: fullText || result.answer, sources, usage: result.usage, streaming: false }
              : m
          )
        );

        // Refresh document usage stats after each completed query
        getDocumentUsage(documentId).then((u) => setUsageModels(u.models));
      } catch (err) {
        const errObj = err as Error & { retryAfter?: number };
        if (errObj.retryAfter) {
          setRetryCountdown(errObj.retryAfter);
          setRetryReason(errObj.message?.includes("high demand") ? "overloaded" : "rate_limit");
          setError("");
        } else {
          setError(errObj.message ?? "Something went wrong.");
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: "Sorry, I couldn't get an answer. Please try again.", streaming: false }
              : m
          )
        );
      } finally {
        setStreaming(false);
      }
    },
    [documentId, provider]
  );

  const providerLabel = provider === "voyage_claude" ? "Claude Sonnet" : "Gemini";
  const providerColor = provider === "voyage_claude" ? "text-purple-600" : "text-blue-600";

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs text-gray-400">Chatting with</p>
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-800 truncate">{filename}</p>
            <span className={`text-xs font-medium ${providerColor}`}>· {providerLabel}</span>
          </div>
        </div>
        {usageModels.length > 0 && (
          <div className="shrink-0">
            <UsageStats models={usageModels} title="This document" />
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-4">
        {messages.length === 0 && (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-gray-400 text-center max-w-xs">
              Ask anything about <span className="font-medium text-gray-600">{filename}</span>.<br />
              The AI will answer using only the document content.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {error && (
          <p className="text-xs text-red-500 text-center">{error}</p>
        )}
        {retryCountdown > 0 && (
          <div className="flex items-center justify-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3a9 9 0 100 18A9 9 0 0012 3z" />
            </svg>
            <span>
              {retryReason === "overloaded"
                ? "Gemini is overloaded right now"
                : "Rate limit reached"}
              {" — ready again in "}
              <span className="font-semibold">{retryCountdown}s</span>
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-4">
        <ChatInput onSend={handleSend} disabled={streaming || retryCountdown > 0} />
        <p className="mt-2 text-center text-xs text-gray-400">
          Answers are grounded in the uploaded document only.
        </p>
      </div>
    </div>
  );
}
