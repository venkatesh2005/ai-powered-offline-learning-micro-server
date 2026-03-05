import os
import re
import pdfplumber
from typing import List, Tuple, Dict

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text directly from PDF using pdfplumber"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    print(f"✅ Extracted {len(page_text)} chars from page {page_num}")
                else:
                    print(f"⚠️  No text found on page {page_num}")
        
        if not text.strip():
            print(f"⚠️  No text could be extracted from the PDF")
            return ""
        
        # Light cleaning - preserve newlines and structure
        # Only remove excessive blank lines (more than 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {str(e)}")
        return ""

def chunk_text(
    text: str,
    chunk_size: int = 150,   # target words per chunk (smaller = more chunks = better retrieval)
    overlap: int = 30,       # words of overlap between consecutive chunks
    max_chars: int = 1200,   # hard cap: keeps chunks within LLM context budget
    min_chunks: int = 4      # if fewer chunks produced, auto-halve chunk_size and retry
) -> List[str]:
    """
    Split text into overlapping word-based chunks.

    Strategy:
    1. Split on paragraph boundaries first to preserve natural structure.
    2. Slide a window of `chunk_size` words with `overlap` carry-over.
    3. Snap window end to nearest paragraph boundary (within 30 words).
    4. Enforce `max_chars` hard cap, truncating at sentence boundary.
    5. De-duplicate consecutive identical chunks.
    """
    if not text or not text.strip():
        return []

    # Step 1: split into paragraphs, track paragraph-start word indices
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    all_words: List[str] = []
    para_break_indices: set = set()

    for para in paragraphs:
        para_break_indices.add(len(all_words))
        all_words.extend(para.split())

    total_words = len(all_words)
    if total_words == 0:
        return []

    # Step 2: sliding window with paragraph-boundary snapping
    raw_chunks: List[str] = []
    stride = max(1, chunk_size - overlap)
    start = 0

    while start < total_words:
        end = min(start + chunk_size, total_words)

        # Snap end to a paragraph break within the next 30 words
        if end < total_words:
            for probe in range(end, min(end + 30, total_words)):
                if probe in para_break_indices:
                    end = probe
                    break

        chunk = " ".join(all_words[start:end]).strip()
        if chunk:
            raw_chunks.append(chunk)

        if end >= total_words:
            break
        start += stride

    # Step 3: enforce max_chars hard cap with sentence-boundary truncation
    final_chunks: List[str] = []
    for chunk in raw_chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
        else:
            truncated = chunk[:max_chars]
            last_period = truncated.rfind('.')
            if last_period > int(max_chars * 0.70):
                truncated = truncated[:last_period + 1]
            final_chunks.append(truncated.strip())

    # Step 4: de-duplicate consecutive identical chunks
    deduped: List[str] = []
    for chunk in final_chunks:
        if not deduped or chunk != deduped[-1]:
            deduped.append(chunk)

    # Step 5: min_chunks guarantee — if too few chunks, halve chunk_size and retry
    if len(deduped) < min_chunks and chunk_size > 40:
        smaller = max(40, chunk_size // 2)
        print(f"⚠️  [chunk_text] Only {len(deduped)} chunks (min={min_chunks}), "
              f"retrying with chunk_size={smaller}")
        return chunk_text(text, chunk_size=smaller, overlap=overlap,
                          max_chars=max_chars, min_chunks=min_chunks)

    # Step 6: report before FAISS indexing
    print(f"\u2702\ufe0f  [chunk_text] {total_words} words \u2192 {len(deduped)} chunks "
          f"(target={chunk_size}w, overlap={overlap}w, max_chars={max_chars})")
    for i, c in enumerate(deduped):
        print(f"   Chunk {i+1:>3}: {len(c.split()):>4} words | {len(c):>5} chars")

    return deduped


def process_pdf(pdf_path: str, chunk_size: int = 150) -> Tuple[str, List[str]]:
    """Extract text from a PDF and return (full_text, chunks)."""
    if not os.path.exists(pdf_path):
        return "", []
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return "", []
    chunks = chunk_text(text, chunk_size)
    return text, chunks


def process_pdf_for_embeddings(
    pdf_path: str,
    chunk_size: int = 150
) -> Tuple[List[str], List[Dict]]:
    """Extract + chunk a PDF, returning (chunks, metadata) ready for FAISS."""
    if not os.path.exists(pdf_path):
        return [], []

    text = extract_text_from_pdf(pdf_path)
    if not text:
        return [], []

    chunks = chunk_text(text, chunk_size)
    metadata = [{"source": pdf_path, "chunk_id": i} for i in range(len(chunks))]

    print(f"\ud83d\udce6 [process_pdf_for_embeddings] {len(chunks)} chunks ready for indexing "
          f"\u2190 {os.path.basename(pdf_path)}")
    return chunks, metadata


def process_directory_for_embeddings(
    directory: str,
    chunk_size: int = 150
) -> Tuple[List[str], List[Dict]]:
    """Process every PDF in a directory. Returns combined (chunks, metadata)."""
    all_chunks: List[str] = []
    all_metadata: List[Dict] = []

    if not os.path.exists(directory):
        return [], []

    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            chunks, metadata = process_pdf_for_embeddings(pdf_path, chunk_size)
            all_chunks.extend(chunks)
            all_metadata.extend(metadata)

    return all_chunks, all_metadata
