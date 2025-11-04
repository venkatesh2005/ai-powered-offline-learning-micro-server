import os
import sys
import time
import hashlib
from typing import List, Dict, Optional
from gpt4all import GPT4All
from cachetools import TTLCache
from functools import lru_cache

# Suppress CUDA warnings (harmless on CPU-only systems)
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

class ChatBot:
    """Optimized Offline AI Chatbot using GPT4All with caching"""
    
    # Response cache: 100 items, 1 hour TTL
    _response_cache = TTLCache(maxsize=100, ttl=3600)
    
    def __init__(self, model_name='orca-mini-3b-gguf2-q4_0.gguf', model_path='models'):
        self.model_name = model_name
        self.model_path = model_path
        self.model = None
        self._model_loaded = False
        
    def load_model(self):
        """Load the GPT4All model with optimized settings"""
        if self._model_loaded:
            return  # Already loaded, skip
            
        if self.model is None:
            print(f"🤖 Loading GPT4All model: {self.model_name}...")
            
            try:
                # Ensure model directory exists
                os.makedirs(self.model_path, exist_ok=True)
                
                # Check if model file exists locally
                model_file_path = os.path.join(self.model_path, self.model_name)
                if not os.path.exists(model_file_path):
                    print(f"❌ Model file not found: {model_file_path}")
                    print(f"   Please download '{self.model_name}' and place it in the '{self.model_path}' directory")
                    raise FileNotFoundError(f"Model file not found: {model_file_path}")
                
                print(f"📂 Loading model from: {model_file_path}")
                
                # Suppress stderr for CUDA warnings
                stderr_backup = sys.stderr
                sys.stderr = open(os.devnull, 'w')
                
                # Load model with optimized settings for speed - OFFLINE MODE
                self.model = GPT4All(
                    model_name=self.model_name,
                    model_path=self.model_path,
                    allow_download=False,  # Disable download for offline mode
                    device='cpu',
                    n_threads=max(1, os.cpu_count() - 1)  # Leave 1 core for system
                )
                
                # Restore stderr
                sys.stderr.close()
                sys.stderr = stderr_backup
                
                self._model_loaded = True
                print("✅ GPT4All model loaded successfully!")
            except Exception as e:
                # Restore stderr in case of error
                if sys.stderr != stderr_backup:
                    sys.stderr.close()
                    sys.stderr = stderr_backup
                print(f"❌ Failed to load model: {e}")
                raise
    
    @staticmethod
    def _create_cache_key(prompt: str, context: str, max_tokens: int, temperature: float) -> str:
        """Create a cache key for responses"""
        key_str = f"{prompt}:{context}:{max_tokens}:{temperature}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def generate_response(self, prompt: str, context: str = None, 
                         max_tokens: int = 150, temperature: float = 0.3) -> tuple:
        """Generate response with caching - OPTIMIZED
        Returns: (response_text, generation_time_seconds)
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._create_cache_key(prompt, context or "", max_tokens, temperature)
        if cache_key in self._response_cache:
            elapsed = time.time() - start_time
            print(f"   ⚡ Cache hit! Response time: {elapsed:.3f}s")
            return self._response_cache[cache_key], elapsed
        
        self.load_model()
        
        # Build optimized prompt
        if context:
            # Use larger context for better information
            context = context[:2000] if len(context) > 2000 else context
            full_prompt = f"""You are a precise educational assistant. Use ONLY the information provided in the context below. Do not add, assume, or create information that is not present.

Context Information:
{context}

Question: {prompt}

Instructions:
- If the question asks for code/program, provide the COMPLETE code exactly as shown in the context
- If the question is theoretical, explain using the exact information from the context
- If the question asks for steps/procedure, list them exactly as provided
- If the answer is NOT in the context, respond: "I don't have this information in the provided materials."
- Do not make up, assume, or hallucinate any information
- Preserve code formatting, variable names, and syntax exactly as given

Answer:"""
        else:
            full_prompt = f"""You are a helpful educational assistant. Answer the following question clearly and concisely.

Question: {prompt}

Answer:"""
        
        try:
            # Optimized generation parameters
            generation_start = time.time()
            with self.model.chat_session():
                response = self.model.generate(
                    full_prompt,
                    max_tokens=max_tokens,  # Balanced for quality/speed
                    temp=temperature,  # Low temp = more focused, faster
                    top_k=40,  # Increased for better sampling
                    top_p=0.4,  # Lower for more focused, faster responses
                    repeat_penalty=1.18,  # Higher to reduce repetition
                    streaming=False
                )
            generation_time = time.time() - generation_start
            
            # Handle both dict and string responses (GPT4All version compatibility)
            if isinstance(response, dict):
                result = response.get('text', response.get('response', str(response))).strip()
            else:
                result = str(response).strip()
            
            # Cache the response
            self._response_cache[cache_key] = result
            
            elapsed = time.time() - start_time
            print(f"   ⏱️  Generation time: {generation_time:.3f}s | Total time: {elapsed:.3f}s")
            
            return result, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ Error generating response: {e}")
            return "I apologize, but I encountered an error. Please try rephrasing your question.", elapsed
    
    def chat_with_context(self, question: str, search_results: List[tuple], 
                         max_tokens: int = 150) -> Dict[str, any]:
        """Generate answer using retrieved context - OPTIMIZED"""
        total_start = time.time()
        
        if not search_results:
            # No context available, use cached response if possible
            answer, gen_time = self.generate_response(question, max_tokens=max_tokens, temperature=0.5)
            total_time = time.time() - total_start
            return {
                'answer': answer,
                'context_used': False,
                'sources': [],
                'generation_time': gen_time,
                'total_time': total_time
            }
        
        # Build optimized context from search results
        context_parts = []
        sources = []
        
        # Detect if question is about programming/code
        is_code_question = any(keyword in question.lower() for keyword in [
            'program', 'code', 'write', 'function', 'void main', 'declare', 
            'implement', 'create', 'dart', 'flutter', 'python', 'java', 'javascript'
        ])
        
        # Use more chunks and longer text for code questions
        if is_code_question:
            num_chunks = min(5, len(search_results))
            max_text_length = 800  # Longer for complete code
        else:
            num_chunks = min(3, len(search_results))
            max_text_length = 500
        
        for i, (text, metadata, score) in enumerate(search_results[:num_chunks]):
            # For code questions, keep complete code blocks without truncation
            if is_code_question and len(text) <= max_text_length:
                context_parts.append(text)
            else:
                # Smart truncation: keep sentences or code blocks
                truncated_text = text[:max_text_length] if len(text) > max_text_length else text
                if len(text) > max_text_length:
                    # Try to end at sentence boundary
                    last_period = truncated_text.rfind('.')
                    if last_period > (max_text_length * 0.7):
                        truncated_text = truncated_text[:last_period + 1]
                context_parts.append(truncated_text)
            
            sources.append({
                'source': metadata.get('source', 'Unknown'),
                'chunk_id': metadata.get('chunk_id', 0),
                'relevance_score': float(score)
            })
        
        # Join context with newlines for better code formatting
        context = "\n\n".join(context_parts)
        
        # Debug: Print context being used
        print(f"🔍 Context for question: {context[:200]}...")
        print(f"📊 Code question detected: {is_code_question}")
        
        # Adjust max_tokens for speed - REDUCED for faster responses
        if is_code_question:
            max_tokens = min(max_tokens, 200)  # Reduced from 300 for faster code responses
        else:
            max_tokens = min(max_tokens, 120)  # Reduced for faster theory responses
        
        # Generate answer with context
        answer, gen_time = self.generate_response(
            question, 
            context=context, 
            max_tokens=max_tokens,
            temperature=0.1  # Lower temp = faster, more focused responses
        )
        
        total_time = time.time() - total_start
        
        return {
            'answer': answer,
            'context_used': True,
            'sources': sources,
            'context': context,
            'generation_time': gen_time,
            'total_time': total_time
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self._response_cache.clear()
    
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model"""
        return {
            'model_name': self.model_name,
            'model_path': self.model_path,
            'is_loaded': self._model_loaded,
            'cache_size': len(self._response_cache)
        }
