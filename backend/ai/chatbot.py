import os
import re
import time
import hashlib
from typing import List, Dict, Optional, Generator
from cachetools import TTLCache

import warnings
import random
warnings.filterwarnings('ignore')

# ── Similarity threshold: chunks below this score are considered off-topic ─────
SIMILARITY_THRESHOLD = 0.45

# ── Pre-canned greeting responses (avoids wasting LLM tokens on hellos) ──────
_GREETING_RESPONSES = {
    'hello': 'Hello! How can I help you with your studies today?',
    'hi': 'Hi there! Ask me anything about your uploaded materials.',
    'hey': 'Hey! Ready to help with your learning materials.',
    'good morning': 'Good morning! What would you like to study today?',
    'good afternoon': 'Good afternoon! How can I assist your learning?',
    'good evening': 'Good evening! What topic shall we explore?',
    'how are you': 'I\'m doing great and ready to help! What would you like to learn?',
    'thanks': 'You\'re welcome! Let me know if you have more questions.',
    'thank you': 'You\'re welcome! Feel free to ask anything else.',
}

# ── Strict code-request phrases (must match an explicit request for code) ─────
_CODE_PHRASES = [
    'write a program', 'write code', 'write a code',
    'write a function', 'write a script',
    'give me code', 'give me the code', 'show me code',
    'code example', 'code snippet', 'code for',
    'implement a', 'implement the',
    'create a program', 'create a function', 'create a script',
    'how to code', 'how to program',
    'void main', 'public static void',
    'print hello world', 'hello world program',
]


# ── Filler prefixes the LLM loves to prepend — stripped in post-processing ────
_FILLER_PREFIXES = [
    r'^(?:in|from|based on|according to|as (?:stated|mentioned|described|shown) in)\s+'
    r'(?:the\s+)?(?:provided\s+)?context\s*\d*\s*[:,.]?\s*',
    r'^the (?:provided |given )?(?:context|document|text|passage)\s*(?:\d*\s*)?'
    r'(?:states?|says?|mentions?|describes?|explains?|shows?|indicates?)\s*'
    r'(?:that\s+)?[:,.]?\s*',
    r'^(?:context\s*\d+\s*[:,.]?\s*)+',
]
_FILLER_RE = re.compile('|'.join(_FILLER_PREFIXES), re.IGNORECASE)


def _is_code_question(text: str) -> bool:
    """Return True only if the question explicitly asks for code."""
    lower = text.lower()
    return any(phrase in lower for phrase in _CODE_PHRASES)


def _detect_greeting(text: str):
    """
    Returns a canned greeting string if *text* is a short small-talk phrase,
    or None if it looks like a real subject question.
    Only triggers on inputs with fewer than 4 words to avoid false positives.
    """
    normalized = text.lower().strip().rstrip('!?.,')
    # Skip anything that looks like a real question (4+ words)
    if len(normalized.split()) > 4:
        return None
    if normalized in _GREETING_RESPONSES:
        return _GREETING_RESPONSES[normalized]
    for key in _GREETING_RESPONSES:
        if normalized.startswith(key) and len(normalized) < len(key) + 4:
            return _GREETING_RESPONSES[key]
    return None


def _clean_response(text: str) -> str:
    """Post-process LLM output: deduplicate paragraphs, trim incomplete sentences."""
    if not text:
        return text

    # Split into paragraphs and deduplicate consecutive identical ones
    paragraphs = text.split('\n\n')
    deduped = []
    for p in paragraphs:
        stripped = p.strip()
        if stripped and (not deduped or stripped != deduped[-1]):
            deduped.append(stripped)

    result = '\n\n'.join(deduped)

    # Trim trailing incomplete sentence (no ending punctuation)
    if result and result[-1] not in '.!?:"\')]}':
        last_period = max(result.rfind('.'), result.rfind('!'), result.rfind('?'))
        if last_period > len(result) * 0.5:
            result = result[:last_period + 1]

    return result.strip()


def _precision_trim(text: str, question: str, is_code: bool) -> str:
    """
    Aggressive post-processing for THEORY answers.
    Goal: return only the 1-3 sentences that directly address the question.

    Steps:
      1. Strip filler prefixes ("In context 1...", "The document states...").
      2. If more than 2 paragraphs, keep only the first.
      3. Extract question keywords then drop sentences that share none.
      4. Cap at 3 sentences.
    """
    if is_code or not text:
        return text

    # 1. Strip filler prefixes
    cleaned = _FILLER_RE.sub('', text).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]

    # 2. If >2 paragraphs, keep only the first
    paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()]
    if len(paragraphs) > 2:
        cleaned = paragraphs[0]

    # 3. Keyword relevance filter
    _STOP = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why',
        'when', 'where', 'which', 'who', 'do', 'does', 'did', 'can', 'could',
        'will', 'would', 'should', 'shall', 'may', 'might', 'has', 'have',
        'had', 'been', 'being', 'for', 'and', 'but', 'or', 'not', 'with',
        'this', 'that', 'these', 'those', 'from', 'into', 'about', 'than',
        'its', 'of', 'in', 'on', 'at', 'to', 'by', 'it', 'be', 'as',
        'you', 'your', 'me', 'my', 'we', 'our', 'they', 'their', 'him',
        'her', 'his', 'she', 'he', 'them', 'us', 'also', 'very', 'just',
        'so', 'too', 'then', 'there', 'here', 'all', 'any', 'each', 'no',
        'yes', 'up', 'out', 'if', 'only', 'own', 'same', 'some', 'such',
    }
    q_words = {
        w.lower() for w in re.findall(r'[a-zA-Z]+', question)
        if len(w) > 2 and w.lower() not in _STOP
    }

    sentences = re.split(r'(?<=[.!?])\s+', cleaned)

    if q_words and len(sentences) > 1:
        scored = []
        for s in sentences:
            s_words = {w.lower() for w in re.findall(r'[a-zA-Z]+', s)}
            overlap = len(q_words & s_words)
            scored.append((overlap, s))

        relevant = [s for score, s in scored if score > 0]
        if not relevant:
            relevant = [scored[0][1]] if scored else sentences[:1]
    else:
        relevant = sentences

    # 4. Cap at 3 sentences
    result = ' '.join(relevant[:3]).strip()

    if result and result[-1] not in '.!?:)]\'"':
        last_end = max(result.rfind('.'), result.rfind('!'), result.rfind('?'))
        if last_end > len(result) * 0.4:
            result = result[:last_end + 1]

    return result.strip() if result else text


def _build_prompt(question: str, context: str = None) -> str:
    """Build TinyLlama chat-format prompt with optional labelled context."""
    if context:
        return (
            "<|system|>\n"
            "You are a precise educational assistant.\n"
            "Answer the question using ONLY the provided context.\n"
            "Provide ONLY the specific sentence(s) that directly answer the question.\n"
            "Do NOT summarize other sections.\n"
            "Do NOT add extra explanation.\n"
            "Do NOT rephrase large parts of the document.\n"
            "If the answer is not clearly present, say:\n"
            "'I don't have this information in the uploaded materials.'\n"
            "<|user|>\n"
            f"{context}\n\n"
            f"Question: {question}\n\n"
            "Answer using only the context above. "
            "Be concise and accurate.\n"
            "<|assistant|>\n"
        )
    else:
        return (
            "<|system|>\n"
            "You are a helpful educational assistant. "
            "Answer clearly and concisely.\n"
            "<|user|>\n"
            f"{question}\n"
            "<|assistant|>\n"
        )


class ChatBot:
    """
    Offline AI Chatbot — llama-cpp-python backend.
    Optimized for Raspberry Pi 5 (8 GB RAM).
    Global singleton: constructed once, model loaded once at startup.
    """
    
    # ── Class-level response cache: 100 items, 1-hour TTL ─────────────────────
    # Shared across all instances — acts as a global cache.
    _response_cache = TTLCache(maxsize=100, ttl=3600)

    # ── Thread safety lock — prevents double-loading in concurrent requests ────
    import threading
    _load_lock = threading.Lock()

    # ── Inference lock — serialises LLM calls so only ONE runs at a time ────────
    # llama-cpp-python's Llama object is NOT thread-safe for concurrent inference.
    # This lock wraps only self.model() — all other endpoints remain non-blocking.
    _inference_lock = threading.Lock()

    def __init__(self, model_path: str):
        """
        Args:
            model_path: Full absolute path to the .gguf model file.
                        Example: '/home/pi/server/backend/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf'
        """
        self.model_path = model_path
        self.model = None
        self._model_loaded = False

    def load_model(self):
        """
        Load TinyLlama via llama-cpp-python.
        Thread-safe: uses a lock so concurrent requests cannot trigger double-loading.
        Safe to call multiple times — loads only once.
        """
        # Fast path — already loaded, no lock needed
        if self._model_loaded:
            return

        with self._load_lock:
            # Double-check inside lock (another thread may have loaded while we waited)
            if self._model_loaded:
                return

            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"❌ Model file not found: {self.model_path}\n"
                    f"   Place the .gguf file at: {self.model_path}"
                )

            n_threads = max(1, (os.cpu_count() or 4) - 1)
            print(f"\n{'='*60}")
            print(f"🤖 [ChatBot] Loading llama-cpp-python model...")
            print(f"   Path    : {self.model_path}")
            print(f"   Threads : {n_threads}")
            print(f"   n_ctx   : 1024")
            print(f"   n_batch : 128")
            print(f"   Backend : CPU (no GPU)")
            print(f"{'='*60}")

            load_start = time.perf_counter()
            try:
                from llama_cpp import Llama
                self.model = Llama(
                    model_path=self.model_path,
                    n_ctx=1024,          # Context window — safe for Pi 5
                    n_threads=n_threads, # CPU threads
                    n_batch=128,         # Prompt batch size
                    n_gpu_layers=0,      # CPU-only
                    use_mmap=True,       # Memory-mapped I/O — reduces RAM copy overhead
                    use_mlock=False,     # Don't lock pages — let OS manage swap
                    verbose=False,       # Suppress llama.cpp C++ logs
                )
                load_time = time.perf_counter() - load_start
                self._model_loaded = True
                print(f"✅ [ChatBot] Model loaded in {load_time:.2f}s")
                print(f"{'='*60}\n")
            except ImportError:
                raise ImportError(
                    "llama-cpp-python is not installed.\n"
                    "Run: pip install llama-cpp-python"
                )
            except Exception as e:
                print(f"❌ [ChatBot] Failed to load model: {e}")
                self.model = None
                self._model_loaded = False
                raise
    
    @staticmethod
    def _create_cache_key(prompt: str, context: str, max_tokens: int, temperature: float) -> str:
        """MD5 cache key — fast, deterministic, avoids re-generating identical queries."""
        key_str = f"{prompt}:{context}:{max_tokens}:{temperature}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def generate_response(
        self,
        prompt: str,
        context: str = None,
        max_tokens: int = 100,
        temperature: float = 0.3,
        top_p: float = 0.8,
        repeat_penalty: float = 1.18,
    ) -> tuple:
        """
        Generate a response using llama-cpp-python with TTL caching.
        Returns: (response_text: str, generation_time_seconds: float)
        """
        t_total_start = time.perf_counter()

        # ── Cache check (avoids LLM call for repeated identical queries) ────────
        cache_key = self._create_cache_key(prompt, context or "", max_tokens, temperature)
        if cache_key in self._response_cache:
            elapsed = time.perf_counter() - t_total_start
            print(f"   ⚡ [ChatBot] Cache hit — skipped LLM call ({elapsed*1000:.1f}ms)")
            return self._response_cache[cache_key], elapsed

        # ── Ensure model is loaded (no-op if already loaded) ─────────────────
        self.load_model()

        if self.model is None:
            return "Model unavailable. Please check server logs.", 0.0

        # ── Build TinyLlama chat-format prompt ───────────────────────────────
        if context:
            context = context[:1500]
        full_prompt = _build_prompt(prompt, context)

        # ── LLM generation with auto-continuation (serialised) ────────────────
        # If finish_reason == "length" the model hit max_tokens mid-sentence.
        # We continue from where it left off, up to MAX_CONTINUATIONS times,
        # by appending the accumulated text to the prompt and calling again.
        # The lock is held for the entire continuation loop so no other request
        # can interleave tokens into a partial response.
        MAX_CONTINUATIONS = 2

        try:
            t_gen_start = time.perf_counter()
            parts: List[str] = []
            total_tokens = 0
            continuation_prompt = full_prompt  # grows with each continuation

            with self._inference_lock:
                for attempt in range(1 + MAX_CONTINUATIONS):
                    output = self.model(
                        continuation_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_k=40,
                        top_p=top_p,
                        repeat_penalty=repeat_penalty,
                        stop=["<|user|>", "<|system|>", "\n\n\n"],
                        echo=False,
                    )

                    chunk_text = output["choices"][0]["text"]
                    finish_reason = output["choices"][0].get("finish_reason", "stop")
                    total_tokens += output.get("usage", {}).get("completion_tokens", 0)
                    parts.append(chunk_text)

                    if finish_reason != "length":
                        # Natural stop — response is complete
                        break

                    if attempt < MAX_CONTINUATIONS:
                        # Truncated — continue from accumulated output so far
                        print(f"   🔄 [ChatBot] finish_reason=length on attempt {attempt+1}, "
                              f"continuing... ({len(''.join(parts))} chars so far)")
                        continuation_prompt = continuation_prompt + "".join(parts)
                    else:
                        print(f"   ⚠️  [ChatBot] Reached max continuations ({MAX_CONTINUATIONS}), "
                              f"stopping.")

            generation_time = time.perf_counter() - t_gen_start
            total_time = time.perf_counter() - t_total_start

            result = "".join(parts).strip()
            if not result:
                result = "I could not generate a response. Please try rephrasing."

            # Store complete assembled response in cache
            self._response_cache[cache_key] = result

            # ── Performance log ───────────────────────────────────────────────
            continuations = len(parts) - 1
            print(f"   ⏱️  [ChatBot] LLM generation : {generation_time*1000:.0f}ms"
                  + (f" ({continuations} continuation{'s' if continuations!=1 else ''})" if continuations else ""))
            print(f"   ⏱️  [ChatBot] Total (w/ cache): {total_time*1000:.0f}ms")
            print(f"   📊 [ChatBot] Tokens generated: {total_tokens}")

            return result, generation_time

        except Exception as e:
            elapsed = time.perf_counter() - t_total_start
            print(f"❌ [ChatBot] Generation error: {e}")
            return "I apologize, but I encountered an error. Please try rephrasing.", elapsed

    # ── Raw completion (NO chat template) — for structured output ─────────
    def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        top_p: float = 0.9,
        repeat_penalty: float = 1.15,
        stop: list = None,
    ) -> tuple:
        """
        Raw text completion — feeds the prompt directly to the model
        WITHOUT wrapping it in <|system|>/<|user|>/<|assistant|> tags.
        Best for structured output like MCQs where the model should
        continue a pattern rather than 'chat'.
        Returns: (completion_text: str, generation_time_seconds: float)
        """
        self.load_model()
        if self.model is None:
            return "", 0.0

        if stop is None:
            stop = []

        t_start = time.perf_counter()
        try:
            with self._inference_lock:
                output = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_k=40,
                    top_p=top_p,
                    repeat_penalty=repeat_penalty,
                    stop=stop,
                    echo=False,
                )
            text = output["choices"][0]["text"]
            tokens = output.get("usage", {}).get("completion_tokens", 0)
            gen_time = time.perf_counter() - t_start
            print(f"   ⏱️  [Completion] {gen_time:.1f}s, {tokens} tokens, {len(text)} chars")
            return text, gen_time
        except Exception as e:
            gen_time = time.perf_counter() - t_start
            print(f"   ❌ [Completion] Error: {e}")
            return "", gen_time

    def chat_with_context(
        self,
        question: str,
        search_results: List[tuple],
        max_tokens: int = 100
    ) -> Dict[str, any]:
        """
        Full RAG pipeline: build context from FAISS results, generate answer.
        Logs timing for every stage to the console.
        """
        t_total = time.perf_counter()

        print(f"\n{'─'*50}")
        print(f"💬 [ChatBot] Question : {question[:80]}{'...' if len(question) > 80 else ''}")
        print(f"📚 [ChatBot] Chunks   : {len(search_results)} retrieved from FAISS")

        # ── Greeting fast-path (skip FAISS + LLM entirely) ────────────────────
        greeting = _detect_greeting(question)
        if greeting:
            total_time = time.perf_counter() - t_total
            print(f"👋 [ChatBot] Greeting detected — skipping FAISS/LLM")
            print(f"{'─'*50}\n")
            return {
                'answer': greeting,
                'context_used': False,
                'sources': [],
                'generation_time': 0.0,
                'total_time': round(total_time, 3)
            }

        # ── No context: refuse rather than hallucinate ────────────────────────
        if not search_results:
            total_time = time.perf_counter() - t_total
            print("⚠️  [ChatBot] No context retrieved — refusing to hallucinate")
            print(f"{'─'*50}\n")
            return {
                'answer': "I don't have this information in the uploaded materials.",
                'context_used': False,
                'sources': [],
                'generation_time': 0.0,
                'total_time': round(total_time, 3)
            }

        # ── Similarity threshold guard — reject off-topic queries ─────────────
        best_score = max(score for _, _, score in search_results)
        print(f"🔢 [ChatBot] Top similarity score: {best_score:.4f}")
        if best_score < SIMILARITY_THRESHOLD:
            total_time = time.perf_counter() - t_total
            print(f"⚠️  [ChatBot] Best score {best_score:.3f} < threshold {SIMILARITY_THRESHOLD} — refusing")
            print(f"{'─'*50}\n")
            return {
                'answer': "I don't have this information in the uploaded materials.",
                'context_used': False,
                'sources': [],
                'generation_time': 0.0,
                'total_time': round(total_time, 3)
            }

        # ── Question type detection ───────────────────────────────────────────
        is_code = _is_code_question(question)

        # ── Generation parameters (THEORY is tighter) ────────────────────────
        if is_code:
            max_char       = 600
            max_tokens     = 250
            temperature    = 0.1
            top_p          = 0.9
            repeat_penalty = 1.18
        else:
            max_char       = 600
            max_tokens     = 120
            temperature    = 0.0
            top_p          = 0.8
            repeat_penalty = 1.2

        print(f"🔍 [ChatBot] Type     : {'CODE' if is_code else 'THEORY'} | "
              f"max_tokens={max_tokens} temp={temperature} top_p={top_p} rp={repeat_penalty}")

        # ── Per-chunk filtering: only inject chunks above threshold ───────────
        filtered = [
            (text, metadata, score)
            for text, metadata, score in search_results
            if score >= SIMILARITY_THRESHOLD
        ]
        print(f"🔎 [ChatBot] Chunks after filter ({SIMILARITY_THRESHOLD}): {len(filtered)}/{len(search_results)}")

        if not filtered:
            total_time = time.perf_counter() - t_total
            print(f"⚠️  [ChatBot] No chunks above threshold — refusing")
            print(f"{'─'*50}\n")
            return {
                'answer': "I don't have this information in the uploaded materials.",
                'context_used': False,
                'sources': [],
                'generation_time': 0.0,
                'total_time': round(total_time, 3)
            }

        # Cap at top 2 highest-scoring chunks (already sorted descending)
        top_chunks = filtered[:2]
        print(f"📌 [ChatBot] Injecting top {len(top_chunks)} chunk(s)")

        # ── Build context string ──────────────────────────────────────────────
        t_ctx = time.perf_counter()
        context_parts = []
        sources = []

        for text, metadata, score in top_chunks:
            if len(text) <= max_char:
                context_parts.append(text)
            else:
                truncated = text[:max_char]
                last_period = truncated.rfind('.')
                if last_period > int(max_char * 0.7):
                    truncated = truncated[:last_period + 1]
                context_parts.append(truncated)

            sources.append({
                'source': metadata.get('source', 'Unknown'),
                'chunk_id': metadata.get('chunk_id', 0),
                'relevance_score': round(float(score), 4)
            })

        labelled = [f"Context {i+1}:\n{part}" for i, part in enumerate(context_parts)]
        context = "\n\n".join(labelled)
        ctx_build_time = time.perf_counter() - t_ctx
        print(f"⏱️  [ChatBot] Context build  : {ctx_build_time*1000:.1f}ms ({len(context)} chars)")

        # ── Generate answer ───────────────────────────────────────────────────
        answer, gen_time = self.generate_response(
            question,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
        )

        # ── Post-process: basic cleanup then precision trim ───────────────────
        answer = _clean_response(answer)
        answer = _precision_trim(answer, question, is_code)

        total_time = time.perf_counter() - t_total

        # ── Summary log ───────────────────────────────────────────────────────
        print(f"⏱️  [ChatBot] LLM generation : {gen_time*1000:.0f}ms")
        print(f"⏱️  [ChatBot] TOTAL request  : {total_time*1000:.0f}ms")
        print(f"📝 [ChatBot] Final answer    : {len(answer)} chars")
        print(f"{'─'*50}\n")

        return {
            'answer': answer,
            'context_used': True,
            'sources': sources,
            'context': context,
            'generation_time': round(gen_time, 3),
            'total_time': round(total_time, 3)
        }

    # ──────────────────────────────────────────────────────────────────────────
    # STREAMING METHODS  (SSE / Server-Sent Events)
    # ──────────────────────────────────────────────────────────────────────────

    def stream_response(
        self,
        prompt: str,
        context: str = None,
        max_tokens: int = 200,
        temperature: float = 0.3
    ) -> Generator[Dict, None, None]:
        """
        Generator: streams tokens one at a time via llama-cpp-python stream=True.

        Yields:
          {"token": str}                         — one per token
          {"done": True, "generation_time": float,
           "cached": bool}                       — final event

        Shares _inference_lock with generate_response(), so streaming and
        non-streaming requests serialise correctly against each other.
        """
        t_start = time.perf_counter()

        # ── Cache hit: re-stream word-by-word for UI consistency ──────────────
        cache_key = self._create_cache_key(prompt, context or "", max_tokens, temperature)
        if cache_key in self._response_cache:
            elapsed = time.perf_counter() - t_start
            print(f"   ⚡ [ChatBot SSE] Cache hit ({elapsed*1000:.1f}ms)")
            words = self._response_cache[cache_key].split(' ')
            for i, word in enumerate(words):
                yield {'token': ('' if i == 0 else ' ') + word}
            yield {'done': True, 'generation_time': round(elapsed, 3), 'cached': True}
            return

        # ── Ensure model is loaded ──────────────────────────────────────
        self.load_model()
        if self.model is None:
            yield {'token': 'Model unavailable. Please check server logs.'}
            yield {'done': True, 'generation_time': 0.0, 'cached': False}
            return

        # ── Build TinyLlama chat-format prompt (identical to generate_response) ──
        if context:
            context = context[:1500]
        full_prompt = _build_prompt(prompt, context)

        # ── Stream tokens (hold inference lock for the full iteration) ─────────
        # Holding the lock here means this stream blocks any concurrent
        # non-streaming generate_response() call, and vice-versa.
        collected: List[str] = []
        t_gen = time.perf_counter()
        try:
            with self._inference_lock:
                for chunk in self.model(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_k=40,
                    top_p=0.8,
                    repeat_penalty=1.2,
                    stop=["<|user|>", "<|system|>", "\n\n\n"],
                    echo=False,
                    stream=True,
                ):
                    token = chunk["choices"][0]["text"]
                    if token:
                        collected.append(token)
                        yield {'token': token}

        except Exception as e:
            print(f"❌ [ChatBot SSE] Generation error: {e}")
            yield {'token': f'\n[Generation error: {e}]'}
            yield {'done': True, 'generation_time': round(time.perf_counter() - t_gen, 3), 'cached': False}
            return

        gen_time = time.perf_counter() - t_gen
        full_text = ''.join(collected).strip()
        if full_text:
            self._response_cache[cache_key] = full_text

        print(f"   ⏱️  [ChatBot SSE] Stream: {gen_time*1000:.0f}ms | {len(collected)} tokens")
        yield {'done': True, 'generation_time': round(gen_time, 3), 'cached': False}

    def chat_with_context_stream(
        self,
        question: str,
        search_results: List[tuple],
        max_tokens: int = 100
    ) -> Generator[Dict, None, None]:
        """
        Full RAG pipeline with SSE streaming.
        Yields same token/done dicts as stream_response(), enriching the
        final 'done' event with sources and context_used.
        """
        print(f"\n{'\u2500'*50}")
        print(f"💬 [ChatBot SSE] Question: {question[:80]}{'...' if len(question) > 80 else ''}")
        print(f"📚 [ChatBot SSE] Chunks  : {len(search_results)} from FAISS")

        # ── Greeting fast-path ───────────────────────────────────────────────
        greeting = _detect_greeting(question)
        if greeting:
            print(f"👋 [ChatBot SSE] Greeting detected — skipping FAISS/LLM")
            yield {'token': greeting}
            yield {'done': True, 'generation_time': 0.0, 'cached': False,
                   'context_used': False, 'sources': []}
            return

        # ── No context: refuse rather than hallucinate ───────────────────────
        if not search_results:
            print("⚠️  [ChatBot SSE] No context — refusing to hallucinate")
            msg = "I don't have this information in the uploaded materials."
            yield {'token': msg}
            yield {'done': True, 'generation_time': 0.0, 'cached': False,
                   'context_used': False, 'sources': []}
            return

        # ── Similarity threshold guard ────────────────────────────────────────
        best_score = max(score for _, _, score in search_results)
        print(f"🔢 [ChatBot SSE] Top similarity score: {best_score:.4f}")
        if best_score < SIMILARITY_THRESHOLD:
            print(f"⚠️  [ChatBot SSE] Best score {best_score:.3f} < threshold — refusing")
            msg = "I don't have this information in the uploaded materials."
            yield {'token': msg}
            yield {'done': True, 'generation_time': 0.0, 'cached': False,
                   'context_used': False, 'sources': []}
            return

        # ── Question type detection ───────────────────────────────────────
        is_code_question = _is_code_question(question)

        if is_code_question:
            max_char   = 600
            max_tokens = 250
        else:
            max_char   = 600
            max_tokens = 120

        # ── Per-chunk filtering: only inject chunks above threshold ───────────
        filtered = [
            (text, metadata, score)
            for text, metadata, score in search_results
            if score >= SIMILARITY_THRESHOLD
        ]
        print(f"🔎 [ChatBot SSE] Chunks after filter ({SIMILARITY_THRESHOLD}): {len(filtered)}/{len(search_results)}")

        if not filtered:
            print(f"⚠️  [ChatBot SSE] No chunks above threshold — refusing")
            msg = "I don't have this information in the uploaded materials."
            yield {'token': msg}
            yield {'done': True, 'generation_time': 0.0, 'cached': False,
                   'context_used': False, 'sources': []}
            return

        # Cap at top 2 highest-scoring chunks (already sorted descending)
        top_chunks = filtered[:2]
        print(f"📌 [ChatBot SSE] Injecting top {len(top_chunks)} chunk(s)")

        # ── Build context ─────────────────────────────────────────────
        context_parts: List[str] = []
        sources: List[dict] = []
        for text, metadata, score in top_chunks:
            if len(text) <= max_char:
                context_parts.append(text)
            else:
                truncated = text[:max_char]
                last_period = truncated.rfind('.')
                if last_period > int(max_char * 0.7):
                    truncated = truncated[:last_period + 1]
                context_parts.append(truncated)
            sources.append({
                'source': metadata.get('source', 'Unknown'),
                'chunk_id': metadata.get('chunk_id', 0),
                'relevance_score': round(float(score), 4)
            })

        labelled = [f"Context {i+1}:\n{part}" for i, part in enumerate(context_parts)]
        context = "\n\n".join(labelled)
        print(f"🔍 [ChatBot SSE] Type: {'CODE' if is_code_question else 'THEORY'} | "
              f"max_tokens={max_tokens} | context={len(context)} chars")

        # ── Stream, merging sources into the final done event ────────────────
        temperature = 0.1 if is_code_question else 0.0
        for event in self.stream_response(
            question, context=context, max_tokens=max_tokens, temperature=temperature
        ):
            if event.get('done'):
                yield {**event, 'context_used': True, 'sources': sources}
            else:
                yield event

    def clear_cache(self) -> int:
        """Clear the TTL response cache. Returns the number of entries removed."""
        count = len(self._response_cache)
        self._response_cache.clear()
        print(f"🧹 [ChatBot] TTL response cache cleared ({count} entries removed).")
        return count

    def get_model_info(self) -> Dict[str, str]:
        """Return model metadata."""
        return {
            'model_path': self.model_path,
            'backend': 'llama-cpp-python',
            'is_loaded': str(self._model_loaded),
            'cache_size': str(len(self._response_cache))
        }
