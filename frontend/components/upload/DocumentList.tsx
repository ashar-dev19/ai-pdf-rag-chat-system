import { type Document } from "@/lib/api";

interface Props {
  documents: Document[];
}

const STATUS_STYLES: Record<Document["status"], string> = {
  processing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-600",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentList({ documents }: Props) {
  if (documents.length === 0) return null;

  return (
    <ul className="flex flex-col gap-2">
      {documents.map((doc) => (
        <li
          key={doc.id}
          className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm"
        >
          <div className="flex flex-col gap-0.5 min-w-0">
            <span className="truncate font-medium text-gray-800">{doc.filename}</span>
            <span className="text-xs text-gray-400">
              {formatBytes(doc.file_size)} · {doc.page_count} page{doc.page_count !== 1 ? "s" : ""}
            </span>
          </div>
          <span
            className={`ml-4 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[doc.status]}`}
          >
            {doc.status}
          </span>
        </li>
      ))}
    </ul>
  );
}
