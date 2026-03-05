import os
import pickle
import time
import numpy as np
from typing import List, Tuple
import faiss
from cachetools import LRUCache

class EmbeddingsManager:
    """Optimized document embeddings manager using FAISS with caching"""
    
    # Query cache: 50 recent queries
    _query_cache = LRUCache(maxsize=50)
    
    def __init__(self, model_name='all-MiniLM-L6-v2', index_path='embeddings_cache/faiss_index.bin', 
                 metadata_path='embeddings_cache/metadata.pkl'):
        self.model_name = model_name
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.model = None
        self.index = None
        self.metadata = []
        self._model_loaded = False
        
    def load_model(self):
        """Load the sentence transformer model (once)."""
        if self._model_loaded:
            return

        if self.model is None:
            print(f"\n📥 [Embeddings] Loading SentenceTransformer: {self.model_name}...")
            t0 = time.perf_counter()
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                self._model_loaded = True
                print(f"✅ [Embeddings] Model loaded in {time.perf_counter()-t0:.2f}s")
            except Exception as e:
                print(f"❌ [Embeddings] Failed to load model: {e}")
                self.model = None
                self._model_loaded = False
    
    def create_embeddings(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """Create embeddings in batches with timing."""
        self.load_model()
        if self.model is None:
            return np.zeros((len(texts), 384), dtype=np.float32)

        batch_size = 32
        embeddings_list = []
        t0 = time.perf_counter()

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            embeddings_list.append(batch_embeddings)

        elapsed = time.perf_counter() - t0
        print(f"⏱️  [Embeddings] Encoded {len(texts)} chunks in {elapsed:.3f}s")
        return np.vstack(embeddings_list) if embeddings_list else np.array([])
    
    def build_index(self, texts: List[str], metadata: List[dict]):
        """Build optimized FAISS index"""
        self.load_model()
        
        print(f"🔨 Building FAISS index with {len(texts)} documents...")
        embeddings = self.create_embeddings(texts, show_progress=True)
        
        # Create optimized FAISS index
        dimension = embeddings.shape[1]
        
        # Use IndexFlatIP for cosine similarity (faster with normalized vectors)
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings.astype('float32'))
        
        # Store texts with metadata
        self.metadata = []
        for i, (text, meta) in enumerate(zip(texts, metadata)):
            meta_copy = meta.copy()
            meta_copy['text'] = text  # Add text to metadata
            self.metadata.append(meta_copy)
        
        self.save_index()
        print("✅ FAISS index built and saved!")
    
    def save_index(self):
        """Save FAISS index and metadata"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    def load_index(self):
        """Load FAISS index and metadata with timing."""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            t0 = time.perf_counter()
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            elapsed = time.perf_counter() - t0
            print(f"✅ [FAISS] Index loaded in {elapsed:.2f}s ({len(self.metadata)} documents)")
            return True
        return False
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, dict, float]]:
        """FAISS cosine-similarity search with per-stage timing logs."""
        # ── Cache check ────────────────────────────────────────────
        cache_key = f"{query}:{top_k}"
        if cache_key in self._query_cache:
            print(f"   ⚡ [FAISS] Cache hit for query ({len(query)} chars)")
            return self._query_cache[cache_key]

        self.load_model()

        if self.model is None:
            print("⚠️  [FAISS] Embeddings model not available, returning empty results")
            return []

        if self.index is None:
            if not self.load_index():
                return []

        # ── Encode query ────────────────────────────────────────────
        t_encode = time.perf_counter()
        try:
            query_embedding = self.model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        except Exception as e:
            print(f"❌ [FAISS] Error encoding query: {e}")
            return []
        encode_time = time.perf_counter() - t_encode

        # ── FAISS search ────────────────────────────────────────────
        t_faiss = time.perf_counter()
        scores, indices = self.index.search(
            query_embedding.astype('float32'),
            min(top_k, len(self.metadata))
        )
        faiss_time = time.perf_counter() - t_faiss

        print(f"⏱️  [FAISS] Encode: {encode_time*1000:.1f}ms | Search: {faiss_time*1000:.1f}ms "
              f"| Total: {(encode_time+faiss_time)*1000:.1f}ms")

        # ── Build results (guard idx == -1 for FAISS unfilled slots) ───────
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue   # FAISS returns -1 when fewer results than top_k
            if 0 <= idx < len(self.metadata):
                score = float(scores[0][i])
                results.append((
                    self.metadata[idx]['text'],
                    self.metadata[idx],
                    score
                ))
                print(f"   📊 [FAISS] Result {i+1}: score={score:.4f} | "
                      f"chunk_id={self.metadata[idx].get('chunk_id', '?')} | "
                      f"{len(self.metadata[idx]['text'].split())} words")

        results.sort(key=lambda x: x[2], reverse=True)
        self._query_cache[cache_key] = results
        return results
    
    def add_documents(self, texts: List[str], metadata: List[dict]):
        """Add new documents to existing index"""
        self.load_model()
        
        if self.index is None:
            self.load_index()
        
        if self.index is None:
            self.build_index(texts, metadata)
            return
        
        # Clear cache when adding new documents
        self._query_cache.clear()
        
        # Create embeddings for new documents
        embeddings = self.create_embeddings(texts)
        
        # Add to index
        self.index.add(embeddings.astype('float32'))
        
        # Store texts with metadata
        for text, meta in zip(texts, metadata):
            meta_copy = meta.copy()
            meta_copy['text'] = text  # Add text to metadata
            self.metadata.append(meta_copy)
        
        # Save updated index
        self.save_index()
        print(f"✅ Added {len(texts)} documents to index!")
    
    def clear_index(self):
        """Clear the current index and metadata"""
        self.index = None
        self.metadata = []
        self._query_cache.clear()
        
        # Remove index files
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
        
        print("🧹 Cleared existing index and metadata")
    
    def clear_query_cache(self) -> int:
        """Clear only the LRU query cache — leaves FAISS index intact.
        Returns the number of entries removed.
        """
        count = len(self._query_cache)
        self._query_cache.clear()
        print(f"🧹 [FAISS] LRU query cache cleared ({count} entries removed).")
        return count

    def get_stats(self) -> dict:
        """Get index statistics"""
        return {
            'total_documents': len(self.metadata),
            'index_loaded': self.index is not None,
            'model_loaded': self._model_loaded,
            'cache_size': len(self._query_cache)
        }
