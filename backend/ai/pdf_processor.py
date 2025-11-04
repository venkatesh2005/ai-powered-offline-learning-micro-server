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

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    if not text:
        return []
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def process_pdf(pdf_path: str, chunk_size: int = 512) -> Tuple[str, List[str]]:
    if not os.path.exists(pdf_path):
        return "", []
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return "", []
    chunks = chunk_text(text, chunk_size)
    return text, chunks

def process_pdf_for_embeddings(pdf_path: str, chunk_size: int = 512) -> Tuple[List[str], List[Dict]]:
    if not os.path.exists(pdf_path):
        return [], []
    
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return [], []
    
    chunks = chunk_text(text, chunk_size)
    metadata = [{"source": pdf_path, "chunk_id": i} for i in range(len(chunks))]
    
    return chunks, metadata

def process_directory_for_embeddings(directory: str, chunk_size: int = 512) -> Tuple[List[str], List[Dict]]:
    all_chunks = []
    all_metadata = []
    
    if not os.path.exists(directory):
        return [], []
    
    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            chunks, metadata = process_pdf_for_embeddings(pdf_path, chunk_size)
            all_chunks.extend(chunks)
            all_metadata.extend(metadata)
    
    return all_chunks, all_metadata
