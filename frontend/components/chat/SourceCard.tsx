import { type SourceCitation } from "@/lib/api";

interface Props {
  source: SourceCitation;
}

export default function SourceCard({ source }: Props) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-600">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="font-medium text-gray-700 truncate">{source.filename}</span>
        <span className="shrink-0 text-gray-400">
          chunk {source.chunk_index} · {Math.round(source.score * 100)}% match
        </span>
      </div>
      <p className="line-clamp-2 text-gray-500">{source.excerpt}</p>
    </div>
  );
}
