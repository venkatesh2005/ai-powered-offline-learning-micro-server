#!/usr/bin/env python3
"""
DEBUG SCRIPT: Analyze Campus Connect PDF Chunks
Examines the actual extracted chunks to identify text extraction issues
"""

import os
import sys
import pickle
import faiss

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from ai.pdf_processor import extract_text_from_pdf, chunk_text

def analyze_pdf_extraction():
    """Analyze the PDF extraction process step by step"""
    
    pdf_path = os.path.join(backend_path, 'resources', 'uploads', 'Campus_Connect_Agile.pdf')
    
    print("="*80)
    print("DEBUG: CAMPUS CONNECT PDF ANALYSIS")
    print("="*80)
    
    # Step 1: Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return
    
    print(f"✅ PDF found: {pdf_path}")
    print(f"📊 File size: {os.path.getsize(pdf_path)} bytes")
    
    # Step 2: Extract raw text
    print("\n" + "="*50)
    print("STEP 1: RAW TEXT EXTRACTION")
    print("="*50)
    
    raw_text = extract_text_from_pdf(pdf_path)
    
    print(f"📝 Extracted text length: {len(raw_text)} characters")
    print(f"📝 First 500 characters:")
    print("-" * 50)
    print(repr(raw_text[:500]))  # Using repr to show hidden characters
    print("-" * 50)
    
    print(f"📝 Last 500 characters:")
    print("-" * 50)
    print(repr(raw_text[-500:]))
    print("-" * 50)
    
    # Step 3: Check for common encoding issues
    print("\n" + "="*50)
    print("STEP 2: ENCODING ANALYSIS")
    print("="*50)
    
    # Check for common signs of encoding issues
    suspicious_chars = ['\\x', '\\u', 'Â', '€', '™', '•']
    encoding_issues = []
    
    for char in suspicious_chars:
        if char in raw_text:
            encoding_issues.append(char)
    
    if encoding_issues:
        print(f"⚠️  Potential encoding issues found: {encoding_issues}")
    else:
        print("✅ No obvious encoding issues detected")
    
    # Check character distribution
    ascii_count = sum(1 for c in raw_text if ord(c) < 128)
    non_ascii_count = len(raw_text) - ascii_count
    
    print(f"📊 ASCII characters: {ascii_count}")
    print(f"📊 Non-ASCII characters: {non_ascii_count}")
    print(f"📊 ASCII ratio: {ascii_count/len(raw_text)*100:.1f}%")
    
    # Step 4: Analyze chunks
    print("\n" + "="*50)
    print("STEP 3: CHUNK ANALYSIS")
    print("="*50)
    
    chunks = chunk_text(raw_text, chunk_size=500, overlap=50)
    print(f"📦 Number of chunks created: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        print(f"\n--- CHUNK {i+1} ---")
        print(f"Length: {len(chunk)} characters")
        print(f"Preview (first 200 chars):")
        print(repr(chunk[:200]))
        print(f"...")
        
        # Check if this chunk looks readable
        words = chunk.split()
        readable_words = sum(1 for word in words if word.isalpha() and len(word) > 2)
        readability_score = readable_words / len(words) if words else 0
        
        print(f"📊 Readability score: {readability_score:.2f} ({readable_words}/{len(words)} words)")
        
        if readability_score < 0.5:
            print("⚠️  LOW READABILITY - This chunk may be corrupted!")
    
    # Step 5: Examine stored embeddings
    print("\n" + "="*50)
    print("STEP 4: STORED EMBEDDINGS ANALYSIS")
    print("="*50)
    
    embeddings_path = os.path.join(backend_path, 'embeddings_cache', 'embeddings.pkl')
    
    if os.path.exists(embeddings_path):
        try:
            with open(embeddings_path, 'rb') as f:
                stored_metadata = pickle.load(f)
            
            print(f"📦 Stored chunks: {len(stored_metadata)}")
            
            for i, metadata in enumerate(stored_metadata[:3]):  # Show first 3
                print(f"\n--- STORED CHUNK {i+1} ---")
                print(f"Source: {metadata.get('source', 'Unknown')}")
                print(f"Chunk ID: {metadata.get('chunk_id', 'Unknown')}")
                stored_text = metadata.get('text', '')
                print(f"Length: {len(stored_text)} characters")
                print(f"Preview:")
                print(repr(stored_text[:200]))
                
        except Exception as e:
            print(f"❌ Error reading stored embeddings: {e}")
    else:
        print("❌ No stored embeddings found")
    
    # Step 6: Recommendations
    print("\n" + "="*50)
    print("STEP 5: RECOMMENDATIONS")
    print("="*50)
    
    if encoding_issues:
        print("🔧 ENCODING FIXES NEEDED:")
        print("   - Add proper UTF-8 handling")
        print("   - Implement text cleaning")
        print("   - Add charset detection")
    
    low_quality_chunks = sum(1 for chunk in chunks 
                            if len(chunk.split()) > 0 and 
                            sum(1 for word in chunk.split() if word.isalpha()) / len(chunk.split()) < 0.5)
    
    if low_quality_chunks > 0:
        print(f"🔧 QUALITY FIXES NEEDED:")
        print(f"   - {low_quality_chunks}/{len(chunks)} chunks have low readability")
        print("   - Implement chunk quality validation")
        print("   - Add text preprocessing")
    
    print("\n✅ Analysis complete! Check debug_chunks_analysis.txt for detailed findings.")

if __name__ == "__main__":
    analyze_pdf_extraction()