from dataclasses import dataclass
from typing import List

import tiktoken

CHUNK_SIZE = 500      # tokens per chunk
CHUNK_OVERLAP = 50   # overlap between consecutive chunks
ENCODING_MODEL = "cl100k_base"  # matches text-embedding-3-small


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    token_count: int


def chunk_text(text: str) -> List[TextChunk]:
    """Split text into overlapping token-based chunks."""
    enc = tiktoken.get_encoding(ENCODING_MODEL)
    tokens = enc.encode(text)

    if not tokens:
        return []

    chunks: List[TextChunk] = []
    start = 0
    index = 0

    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text_str = enc.decode(chunk_tokens).strip()

        if chunk_text_str:
            chunks.append(TextChunk(
                chunk_index=index,
                text=chunk_text_str,
                token_count=len(chunk_tokens),
            ))
            index += 1

        if end == len(tokens):
            break

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks
