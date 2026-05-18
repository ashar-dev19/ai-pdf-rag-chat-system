import { notFound } from "next/navigation";
import { getDocument } from "@/lib/api";
import ChatInterface from "./ChatInterface";

interface Props {
  params: Promise<{ documentId: string }>;
}

export default async function ChatPage({ params }: Props) {
  const { documentId } = await params;

  let document;
  try {
    document = await getDocument(documentId);
  } catch {
    notFound();
  }

  if (document.status !== "ready") {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-medium text-gray-700">Document is still processing…</p>
          <p className="mt-1 text-xs text-gray-400">
            Come back in a few seconds once status shows <span className="font-medium text-green-600">ready</span>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ChatInterface
      documentId={document.id}
      filename={document.filename}
      provider={document.provider}
    />
  );
}
