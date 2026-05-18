import { type SourceCitation, type UsageInfo } from "@/lib/api";
import SourceCard from "./SourceCard";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  usage?: UsageInfo;
  streaming?: boolean;
}

const MODEL_LABELS: Record<string, string> = {
  "gemini-2.5-flash": "Gemini 2.5 Flash",
  "claude-haiku-4-5-20251001": "Claude Haiku",
  "claude-sonnet-4-6": "Claude Sonnet",
};

interface Props {
  message: Message;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
        }`}
      >
        {message.content}
        {message.streaming && (
          <span className="ml-1 inline-block h-3.5 w-0.5 animate-pulse bg-current opacity-70" />
        )}
      </div>

      {!isUser && message.usage && !message.streaming && (
        <p className="text-xs text-gray-400 ml-1">
          {MODEL_LABELS[message.usage.model] ?? message.usage.model}
          {" · "}
          {message.usage.input_tokens.toLocaleString()} in
          {" · "}
          {message.usage.output_tokens.toLocaleString()} out
        </p>
      )}

      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="flex flex-col gap-1.5 w-full max-w-[80%]">
          <p className="text-xs text-gray-400 ml-1">Sources</p>
          {message.sources.map((source, i) => (
            <SourceCard key={i} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}
