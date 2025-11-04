import os
import pickle
import numpy as np
from typing import List, Tuple
import faiss
from cachetools import LRUCache
from functools import lru_cache

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
        """Load the sentence transformer model (once)"""
        if self._model_loaded:
            return  # Already loaded
            
        if self.model is None:
            print(f"📥 Loading embeddings model: {self.model_name}...")
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                self._model_loaded = True
                print("✅ Embeddings model loaded!")
            except Exception as e:
                print(f"❌ Failed to load embeddings model: {e}")
                self.model = None
                self._model_loaded = False
    
    def create_embeddings(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """Create embeddings with optional progress bar"""
        self.load_model()
        if self.model is None:
            return np.zeros((len(texts), 384), dtype=np.float32)
        
        # Batch processing for efficiency
        batch_size = 32
        embeddings_list = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch, 
                show_progress_bar=show_progress and i == 0,  # Show once
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for better similarity
            )
            embeddings_list.append(batch_embeddings)
        
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
        """Load FAISS index and metadata"""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            print(f"✅ Loaded index with {len(self.metadata)} documents!")
            return True
        return False
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, dict, float]]:
        """Optimized search with caching"""
        # Check cache first
        cache_key = f"{query}:{top_k}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        self.load_model()
        
        # If model failed to load, return empty results
        if self.model is None:
            print("⚠️  Embeddings model not available, returning empty results")
            return []
        
        if self.index is None:
            if not self.load_index():
                return []
        
        # Create query embedding
        try:
            query_embedding = self.model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        except Exception as e:
            print(f"❌ Error encoding query: {e}")
            return []
        
        # Search (using cosine similarity via inner product)
        scores, indices = self.index.search(query_embedding.astype('float32'), min(top_k, len(self.metadata)))
        
        # Return results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata) and idx >= 0:
                results.append((
                    self.metadata[idx]['text'],
                    self.metadata[idx],
                    float(scores[0][i])
                ))
        
        # Cache results
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
    
    def get_stats(self) -> dict:
        """Get index statistics"""
        return {
            'total_documents': len(self.metadata),
            'index_loaded': self.index is not None,
            'model_loaded': self._model_loaded,
            'cache_size': len(self._query_cache)
        }
