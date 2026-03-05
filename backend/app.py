from flask import Flask, request, jsonify, session, send_file, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from flask_compress import Compress
from werkzeug.utils import secure_filename
import os
import time
import threading
import queue
import json
import psutil
from datetime import datetime
from functools import wraps
from config import config
from database.models import db, User, Resource, Quiz, QuizResult, Notification, ChatHistory
from database.init_db import init_database, seed_sample_resources
from ai.embeddings import EmbeddingsManager
from ai.pdf_processor import process_pdf_for_embeddings, process_directory_for_embeddings
from ai.chatbot import ChatBot
from quiz_generator import quiz_generator

# Initialize Flask app
app = Flask(__name__, static_folder='static/dist', static_url_path='')

# Load configuration based on environment
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])
config[env].init_app(app)

# Enable response compression for faster API responses
Compress(app)

# Enable CORS for React frontend with session support
# Added expose_headers for file downloads to work on mobile
CORS(app, 
     supports_credentials=True,
     origins=app.config['CORS_ORIGINS'],
     allow_headers=['Content-Type', 'Authorization'],
     expose_headers=['Content-Disposition', 'Content-Type', 'Content-Length'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
)

# Initialize database
db.init_app(app)

# Initialize AI components
embeddings_manager = None
chatbot = None
_startup_complete = False


def get_embeddings_manager():
    """Return the global EmbeddingsManager (preloaded at startup)."""
    global embeddings_manager
    if embeddings_manager is None:
        embeddings_manager = EmbeddingsManager(
            model_name=app.config['EMBEDDINGS_MODEL'],
            index_path=app.config['FAISS_INDEX_PATH'],
            metadata_path=app.config['EMBEDDINGS_CACHE_PATH']
        )
    return embeddings_manager


def get_chatbot():
    """Return the global ChatBot (preloaded at startup)."""
    global chatbot
    if chatbot is None:
        model_file = os.path.join(app.config['MODELS_PATH'], app.config['GPT4ALL_MODEL'])
        chatbot = ChatBot(model_path=model_file)
        chatbot.load_model()
    return chatbot


def _preload_ai_models():
    """Background thread: load embeddings + LLM at server startup."""
    global embeddings_manager, chatbot, _startup_complete
    t0 = time.perf_counter()
    print("\n" + "="*60)
    print("🚀 [Startup] Background AI preload thread started")
    print("="*60)

    try:
        # ── Step 1: Load embeddings model ─────────────────────────────
        with app.app_context():
            em = get_embeddings_manager()
            em.load_model()
            em.load_index()   # Pre-warm FAISS index into RAM

        # ── Step 2: Load LLM ──────────────────────────────────────
        with app.app_context():
            bot = get_chatbot()   # triggers ChatBot.load_model() internally
            quiz_generator.set_chatbot(bot)  # wire LLM into quiz generator

        total = time.perf_counter() - t0
        _startup_complete = True
        print(f"\n✅ [Startup] AI preload complete in {total:.1f}s — server is READY")
        print("="*60 + "\n")

    except Exception as exc:
        print(f"❌ [Startup] AI preload failed: {exc}")
        print("   Server still running — models will load on first request.")
        print("="*60 + "\n")

# Initialize database on first run
with app.app_context():
    init_database(app)
    seed_sample_resources(app)

# ── Cache helpers ─────────────────────────────────────────────────────────────

def _clear_diskcache() -> int:
    """
    Clear the diskcache directory if it exists.
    Returns the number of entries removed (0 if diskcache not in use).
    Never raises — safe to call unconditionally.
    """
    try:
        import diskcache
        cache_dir = os.path.join(os.path.dirname(__file__), 'diskcache')
        if not os.path.isdir(cache_dir):
            return 0
        with diskcache.Cache(cache_dir) as dc:
            count = len(dc)
            dc.clear()
        print(f"🧹 [diskcache] Cleared {count} entries from {cache_dir}")
        return count
    except ImportError:
        return 0   # diskcache not installed — silently skip
    except Exception as e:
        print(f"⚠️  [diskcache] Error clearing disk cache: {e}")
        return 0


def _flush_caches_at_startup():
    """
    Wipe all in-process caches once at startup before serving any requests.
    Prevents stale TTL/LRU entries from a previous hot-reload surviving into
    a new process.  On a cold first boot all caches are already empty, so
    this is effectively a no-op.
    """
    ttl_count = len(ChatBot._response_cache)
    ChatBot._response_cache.clear()

    lru_count = len(EmbeddingsManager._query_cache)
    EmbeddingsManager._query_cache.clear()

    disk_count = _clear_diskcache()

    print(
        f"🧹 [Startup] Cache flush complete — "
        f"TTL={ttl_count} | LRU={lru_count} | Disk={disk_count}"
    )


_flush_caches_at_startup()

# Start background AI preload (non-blocking — first request will still work even if
# preload hasn't finished, because get_chatbot/get_embeddings_manager are also lazy)
threading.Thread(target=_preload_ai_models, daemon=True, name='AI-Preload').start()

# ──────────────────────────────────────────────────────────
# LLM CHAT QUEUE
# ──────────────────────────────────────────────────────────
# A single background worker drains the queue, ensuring only ONE call to
# bot.chat_with_context() is in flight at any time.
#
# Each job is a dict:
#   { 'question': str, 'search_results': list,
#     'result_event': threading.Event, 'result': [None] }
#
# The HTTP handler blocks on result_event (up to CHAT_QUEUE_TIMEOUT seconds).
# If the queue is full (> CHAT_QUEUE_MAX) we return 503 immediately.
# ──────────────────────────────────────────────────────────

CHAT_QUEUE_MAX     = 10    # Reject (503) if more than this many are waiting
CHAT_QUEUE_TIMEOUT = 120   # Seconds a request will wait before returning 503

_chat_work_queue: queue.Queue = queue.Queue()


def _chat_worker():
    """Single background thread: processes LLM jobs one at a time."""
    print("💬 [ChatQueue] Worker thread started")
    while True:
        job = _chat_work_queue.get()          # blocks until a job arrives
        if job is None:                       # sentinel — shut down signal
            break
        try:
            bot    = get_chatbot()
            result = bot.chat_with_context(job['question'], job['search_results'])
            job['result'][0] = result
        except Exception as exc:
            job['result'][0] = {'error': str(exc)}
        finally:
            job['result_event'].set()         # wake up the waiting HTTP handler
            _chat_work_queue.task_done()


threading.Thread(target=_chat_worker, daemon=True, name='Chat-Worker').start()

# ==================== MIDDLEWARE ====================

@app.before_request
def log_session_info():
    """Log session information for debugging"""
    if request.method != 'OPTIONS':  # Skip OPTIONS preflight requests
        print(f"\n🔍 Request: {request.method} {request.path}")
        print(f"   From: {request.remote_addr}")
        print(f"   Origin: {request.headers.get('Origin', 'None')}")
        print(f"   Cookies received: {list(request.cookies.keys())}")
        print(f"   Session data: {dict(session)}")
        print(f"   Has user_id: {'user_id' in session}")

@app.after_request
def after_request(response):
    """Ensure CORS headers are set on all responses"""
    origin = request.headers.get('Origin')
    if origin and origin in app.config['CORS_ORIGINS']:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_file_size(file_path):
    """Get file size in bytes"""
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0

def require_admin(f):
    """Decorator: reject non-admin users with 403."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapper

def require_login(f):
    """Decorator: reject unauthenticated users with 401."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return wrapper

# ==================== ROUTES ====================

# Serve React App (only in production when build exists)
@app.route('/')
def serve_root():
    """Serve React app root or API info"""
    # Check if production build exists
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        # Check if there are actual build files (not just placeholder)
        assets_path = os.path.join(app.static_folder, 'assets')
        if os.path.exists(assets_path) and os.listdir(assets_path):
            return send_from_directory(app.static_folder, 'index.html')
    
    # In development, return API info
    return jsonify({
        'name': 'AI Learning Hub API',
        'version': '1.0.0',
        'status': 'running',
        'message': 'Backend API is running. For development, use the React dev server at http://localhost:3000',
        'endpoints': {
            'stats': '/api/stats',
            'login': '/api/login',
            'logout': '/api/logout',
            'resources': '/api/resources',
            'chat': '/api/chat',
            'quizzes': '/api/quizzes',
            'admin': '/api/admin/dashboard'
        }
    })

# ==================== CACHE MANAGEMENT ====================

@app.route('/api/clear-cache', methods=['POST'])
def api_clear_cache():
    """
    Admin-only endpoint to flush all in-process caches.
    Clears: ChatBot TTL cache, EmbeddingsManager LRU cache, diskcache (if used).
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    # 1 — ChatBot TTL response cache
    bot = chatbot
    if bot is not None:
        ttl_cleared = bot.clear_cache()
    else:
        ttl_cleared = len(ChatBot._response_cache)
        ChatBot._response_cache.clear()
        print(f"🧹 [API/clear-cache] TTL cleared via class ref ({ttl_cleared} entries)")

    # 2 — EmbeddingsManager LRU query cache
    em = embeddings_manager
    if em is not None:
        lru_cleared = em.clear_query_cache()
    else:
        lru_cleared = len(EmbeddingsManager._query_cache)
        EmbeddingsManager._query_cache.clear()
        print(f"🧹 [API/clear-cache] LRU cleared via class ref ({lru_cleared} entries)")

    # 3 — diskcache
    disk_cleared = _clear_diskcache()

    print(
        f"✅ [API /api/clear-cache] Done — "
        f"TTL={ttl_cleared} | LRU={lru_cleared} | Disk={disk_cleared}"
    )

    return jsonify({
        'status': 'cache cleared',
        'cleared': {
            'ttl_cache':  ttl_cleared,
            'lru_cache':  lru_cleared,
            'disk_cache': disk_cleared,
        }
    })


# Serve static assets (only in production)
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from React build"""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # For production SPA routing, return index.html
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        return send_from_directory(app.static_folder, 'index.html')
    return jsonify({'error': 'Not found'}), 404

# ==================== API ROUTES ====================

@app.route('/api/stats')
def api_stats():
    """Get dashboard stats"""
    stats = {
        'user_count': User.query.count(),
        'resource_count': Resource.query.count(),
        'quiz_count': Quiz.query.count(),
        'chat_count': ChatHistory.query.count(),
        'notifications': [
            {
                'id': n.id,
                'message': n.message,
                'type': n.notification_type,  # Fixed: use notification_type, not type
                'created_at': n.created_at.isoformat()
            }
            for n in Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).limit(5).all()
        ],
        'recent_resources': [
            {
                'id': r.id,
                'title': r.title,
                'category': r.category,
                'uploaded_at': r.uploaded_at.isoformat(),
                'indexed': r.indexed
            }
            for r in Resource.query.order_by(Resource.uploaded_at.desc()).limit(6).all()
        ]
    }
    return jsonify(stats)

@app.route('/api/login', methods=['POST'])
def api_login():
    """Optimized login with password hashing"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    # Use password hashing for security
    if user and user.check_password(password):
        # Clear any existing session first
        session.clear()
        
        # Set session data
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        session.permanent = True
        session.modified = True  # Force session save
        
        user.last_login = datetime.now()
        db.session.commit()
        
        # Debug: Print session info
        print(f"✅ Login successful - User: {username}, Session ID: {session.get('user_id')}, Admin: {session.get('is_admin')}")
        print(f"   Session cookie will be sent to: {request.remote_addr}")
        print(f"   Session modified: {session.modified}")
        
        response_data = {
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin
            }
        }
        
        print(f"📤 Sending response: {response_data}")
        
        response = jsonify(response_data)
        
        # Explicitly set CORS headers to allow credentials
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        
        print(f"   Response headers: {dict(response.headers)}")
        
        return response
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/signup', methods=['POST'])
def api_signup():
    """Optimized signup with password hashing"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # Validation
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400
    
    if len(username) < 3:
        return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
    
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 409
    
    # Create user with hashed password
    new_user = User(username=username, is_admin=False)
    new_user.set_password(password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'is_admin': new_user.is_admin
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to create account'}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Logout API endpoint"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/resources')
def api_resources():
    """Optimized resources list with query optimization"""
    search_query = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    
    # Build optimized query
    query = Resource.query
    
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Resource.title.ilike(search_pattern),
                Resource.description.ilike(search_pattern),
                Resource.filename.ilike(search_pattern)
            )
        )
    
    if category:
        query = query.filter_by(category=category)
    
    # Get resources with optimized ordering
    resources_list = query.order_by(Resource.uploaded_at.desc()).all()
    
    # Get distinct categories efficiently
    categories = db.session.query(Resource.category).distinct().filter(Resource.category.isnot(None)).all()
    categories = [c[0] for c in categories]
    
    return jsonify({
        'resources': [
            {
                'id': r.id,
                'title': r.title,
                'description': r.description,
                'filename': r.filename,
                'category': r.category,
                'file_size': r.file_size,
                'uploaded_at': r.uploaded_at.isoformat(),
                'indexed': r.indexed
            }
            for r in resources_list
        ],
        'categories': categories
    })

@app.route('/api/resources/download/<int:resource_id>')
def api_download_resource(resource_id):
    """Download a resource - mobile compatible"""
    resource = Resource.query.get_or_404(resource_id)
    
    if not os.path.exists(resource.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    
    try:
        # Use send_file with proper MIME type detection
        return send_file(
            resource.file_path,
            as_attachment=True,
            download_name=resource.filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        print(f"Error serving file: {e}")
        return jsonify({'error': f'Failed to serve file: {str(e)}'}), 500

@app.route('/api/resources/<int:resource_id>/download')
def api_resource_download(resource_id):
    """Alternative download endpoint - mobile compatible"""
    resource = Resource.query.get_or_404(resource_id)
    
    if not os.path.exists(resource.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    
    try:
        return send_file(
            resource.file_path,
            as_attachment=True,
            download_name=resource.filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        print(f"Error serving file: {e}")
        return jsonify({'error': f'Failed to serve file: {str(e)}'}), 500

@app.route('/api/resources/<int:resource_id>/view')
def api_resource_view(resource_id):
    """View a resource inline (for PDFs) - mobile compatible"""
    resource = Resource.query.get_or_404(resource_id)
    
    if not os.path.exists(resource.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    
    try:
        # Determine mimetype based on file extension
        mimetype_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'txt': 'text/plain',
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo',
            'mkv': 'video/x-matroska'
        }
        
        mimetype = mimetype_map.get(resource.file_type, 'application/octet-stream')
        
        # Send file with inline disposition for viewing in browser
        return send_file(
            resource.file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=resource.filename
        )
    except Exception as e:
        print(f"Error serving file for viewing: {e}")
        return jsonify({'error': f'Failed to serve file: {str(e)}'}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    Chat endpoint backed by a single-worker LLM queue.

    Flow:
      1. FAISS search (fast, runs outside the queue — no blocking).
      2. Job submitted to _chat_work_queue.
      3. This thread blocks on a per-job Event (up to CHAT_QUEUE_TIMEOUT s).
      4. Worker thread processes jobs one at a time and signals the Event.

    If the queue is already full (> CHAT_QUEUE_MAX waiting), returns 503.
    """
    request_start = time.perf_counter()
    data = request.get_json()
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    # ── Reject early if queue is overloaded ───────────────────────────────────
    queue_depth = _chat_work_queue.qsize()
    if queue_depth >= CHAT_QUEUE_MAX:
        print(f"⚠️  [ChatQueue] Rejected — queue full ({queue_depth} waiting)")
        return jsonify({
            'error': 'Server is busy. Please try again in a moment.',
            'status': 'busy',
            'queue_depth': queue_depth
        }), 503

    try:
        # ── FAISS search (runs on the HTTP thread — fast, no LLM needed) ─────
        t_search = time.perf_counter()
        em = get_embeddings_manager()
        search_results = em.search(question, top_k=5)
        search_time = time.perf_counter() - t_search

        # ── Submit job to the worker queue ────────────────────────────────────
        position = _chat_work_queue.qsize() + 1   # approximate position
        result_holder = [None]
        done_event = threading.Event()

        job = {
            'question':       question,
            'search_results': search_results,
            'result_event':   done_event,
            'result':         result_holder,
        }
        _chat_work_queue.put(job)
        print(f"📥 [ChatQueue] Queued (position ~{position}) — '{question[:60]}'")

        # ── Block until the worker finishes (or timeout) ──────────────────────
        finished = done_event.wait(timeout=CHAT_QUEUE_TIMEOUT)
        if not finished:
            print(f"⏰ [ChatQueue] Timed out after {CHAT_QUEUE_TIMEOUT}s")
            return jsonify({
                'error': 'Request timed out waiting for the model. Please try again.',
                'status': 'timeout'
            }), 503

        result = result_holder[0]

        # Worker captured an exception
        if isinstance(result, dict) and 'error' in result and 'answer' not in result:
            raise RuntimeError(result['error'])

        total_request_time = time.perf_counter() - request_start
        print(f"⏱️  [API /chat] FAISS: {search_time*1000:.0f}ms | "
              f"LLM: {result.get('generation_time', 0)*1000:.0f}ms | "
              f"Total: {total_request_time*1000:.0f}ms | "
              f"Queue wait: {(total_request_time - search_time - result.get('total_time', 0))*1000:.0f}ms")

        # ── Persist chat history ──────────────────────────────────────────────
        if 'user_id' in session:
            conversation_id = data.get('conversation_id')
            chat_entry = ChatHistory(
                user_id=session['user_id'],
                conversation_id=conversation_id,
                question=question,
                answer=result['answer'],
                context_used=result.get('context', '')
            )
            db.session.add(chat_entry)

            if conversation_id:
                from database.models import Conversation
                conversation = Conversation.query.get(conversation_id)
                if conversation:
                    conversation.updated_at = datetime.now()

            db.session.commit()

        return jsonify({
            'answer':          result['answer'],
            'sources':         result.get('sources', []),
            'context_used':    result.get('context_used', False),
            'generation_time': result.get('generation_time', 0),
            'total_time':      round(total_request_time, 3),
            'search_time':     round(search_time, 3),
            'queue_position':  position,
        })

    except Exception as e:
        print(f"❌ Chat error: {e}")
        return jsonify({
            'answer': "I apologize, but I encountered an error. Please try again.",
            'error': str(e) if app.debug else "Internal error"
        }), 500


@app.route('/api/chat/stream', methods=['POST'])
def api_chat_stream():
    """
    Streaming chat endpoint — Server-Sent Events (SSE).

    Uses llama-cpp-python stream=True so tokens are pushed to the client
    as they are generated.  Does NOT go through the queue worker; it holds
    the ChatBot._inference_lock directly, so it serialises correctly with
    any concurrent non-streaming /api/chat requests.

    SSE event format:
      data: {"token": "<text>"}          — one per generated token
      data: {"done": true, "generation_time": 1.23, "cached": false,
             "context_used": true, "sources": [...],
             "search_time": 0.05}        — final event
      data: {"error": "<msg>"}           — on failure

    Client usage (JavaScript):
      const es = new EventSource(...)  is NOT used here because the request
      has a POST body.  Use fetch() + ReadableStream instead:

        const resp = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({ question: '...' })
        });
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const lines = decoder.decode(value).split('\\n');
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const event = JSON.parse(line.slice(6));
                if (event.token) process(event.token);
                if (event.done)  finish(event);
            }
        }
    """
    data = request.get_json()
    question = (data or {}).get('question', '').strip()
    if not question:
        return jsonify({'error': 'Question is required'}), 400

    # Reject if queue is also overloaded (shared capacity indicator)
    if _chat_work_queue.qsize() >= CHAT_QUEUE_MAX:
        return jsonify({'error': 'Server is busy. Please try again.', 'status': 'busy'}), 503

    def event_generator():
        """Generator that yields SSE-formatted lines."""
        def sse(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        try:
            # ── FAISS search (fast, runs before acquiring inference lock) ────
            t_search = time.perf_counter()
            em = get_embeddings_manager()
            search_results = em.search(question, top_k=5)
            search_time = round(time.perf_counter() - t_search, 3)

            # ── Stream tokens from the model ────────────────────────────
            bot = get_chatbot()
            for event in bot.chat_with_context_stream(question, search_results):
                if event.get('done'):
                    # Enrich final event with search metadata
                    yield sse({**event, 'search_time': search_time})
                else:
                    yield sse(event)

            # ── Persist chat history after stream completes ───────────────
            # We don’t have the full answer text here (it was streamed),
            # so look it up from cache via the same question.
            with app.app_context():
                if 'user_id' in session:
                    cached_answer = bot._response_cache.get(
                        bot._create_cache_key(question, '', 100, 0.3), ''
                    ) or bot._response_cache.get(
                        bot._create_cache_key(question, '', 150, 0.1), ''
                    ) or '[streamed]'
                    conversation_id = data.get('conversation_id')
                    chat_entry = ChatHistory(
                        user_id=session['user_id'],
                        conversation_id=conversation_id,
                        question=question,
                        answer=cached_answer,
                        context_used='[streamed]'
                    )
                    db.session.add(chat_entry)
                    if conversation_id:
                        from database.models import Conversation
                        conv = Conversation.query.get(conversation_id)
                        if conv:
                            conv.updated_at = datetime.now()
                    db.session.commit()

        except Exception as e:
            print(f"❌ [SSE] Error: {e}")
            yield sse({'error': str(e) if app.debug else 'Internal error'})

    return Response(
        stream_with_context(event_generator()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',   # Disable nginx buffering if behind a proxy
            'Connection':       'keep-alive',
        }
    )


@app.route('/api/status', methods=['GET'])
def api_status():
    """Server readiness + AI status endpoint.\n    Poll this on the frontend to know when models have loaded.\n    """
    em   = get_embeddings_manager()
    bot  = chatbot  # Don't force-load here; just report current state
    return jsonify({
        'server': 'online',
        'startup_complete': _startup_complete,
        'embeddings_loaded': em._model_loaded if em else False,
        'faiss_index_loaded': em.index is not None if em else False,
        'chatbot_loaded': bot._model_loaded if bot else False,
        'documents_indexed': len(em.metadata) if em else 0,
        'chat_queue_depth': _chat_work_queue.qsize(),
        'chat_queue_max': CHAT_QUEUE_MAX,
    })


@app.route('/api/index-resources', methods=['POST'])
def api_index_resources():
    """Index all PDF resources for AI search with detailed debugging"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = os.path.join(app.config['BASE_DIR'], f'debug_indexing_{timestamp}.txt')
        
        debug_content = []
        debug_content.append("="*80)
        debug_content.append(f"INDEXING DEBUG LOG - {datetime.datetime.now()}")
        debug_content.append("="*80)
        debug_content.append("")
        
        # Get all unindexed PDF resources (or force reindex all if requested)
        force_reindex = request.json.get('force_reindex', False) if request.is_json else False
        
        if force_reindex:
            # Force reindex all PDFs
            pdf_resources = Resource.query.filter_by(file_type='pdf').all()
            debug_content.append("🔄 FORCE REINDEX: Processing ALL PDFs")
            # Clear existing index
            em = get_embeddings_manager()
            em.clear_index()
        else:
            pdf_resources = Resource.query.filter_by(file_type='pdf', indexed=False).all()
            debug_content.append(f"📋 Found {len(pdf_resources)} unindexed PDFs")
        
        if not pdf_resources:
            debug_content.append("ℹ️ No PDFs to process")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_content))
            return jsonify({'message': 'No new PDFs to index', 'count': 0, 'debug_file': debug_file})
        
        all_chunks = []
        all_metadata = []
        
        for i, resource in enumerate(pdf_resources):
            debug_content.append(f"\n--- PROCESSING PDF {i+1}/{len(pdf_resources)} ---")
            debug_content.append(f"📄 File: {resource.filename}")
            debug_content.append(f"📍 Path: {resource.file_path}")
            debug_content.append(f"📊 Exists: {os.path.exists(resource.file_path)}")
            
            if os.path.exists(resource.file_path):
                try:
                    # Extract text once and reuse for both debug logging and chunking
                    from ai.pdf_processor import extract_text_from_pdf, chunk_text
                    raw_text = extract_text_from_pdf(resource.file_path)
                    
                    debug_content.append(f"📝 Raw text length: {len(raw_text)} characters")
                    debug_content.append(f"📝 First 200 chars: {repr(raw_text[:200])}")
                    
                    # Calculate readability
                    words = raw_text.split()
                    if words:
                        readable_words = sum(1 for word in words if word.isalpha() and len(word) > 1)
                        readability = readable_words / len(words)
                        debug_content.append(f"📊 Readability score: {readability:.3f} ({readable_words}/{len(words)} words)")
                    
                    # Build chunks from already-extracted text (avoids re-extracting the PDF)
                    chunks = chunk_text(raw_text)
                    metadata = [{"source": resource.file_path, "chunk_id": i} for i in range(len(chunks))]
                    
                    debug_content.append(f"📦 Generated {len(chunks)} chunks")
                    
                    # Show each chunk
                    for j, (chunk, meta) in enumerate(zip(chunks, metadata)):
                        debug_content.append(f"\n  CHUNK {j+1}:")
                        debug_content.append(f"  📏 Length: {len(chunk)} characters")
                        debug_content.append(f"  📝 Full Content:\n{chunk}")
                        
                        # Chunk quality check
                        chunk_words = chunk.split()
                        if chunk_words:
                            chunk_readable = sum(1 for word in chunk_words if word.isalpha() and len(word) > 1)
                            chunk_readability = chunk_readable / len(chunk_words)
                            debug_content.append(f"  📊 Chunk readability: {chunk_readability:.3f}")
                            
                            if chunk_readability < 0.3:
                                debug_content.append(f"  ⚠️ LOW QUALITY CHUNK!")
                            else:
                                debug_content.append(f"  ✅ Good quality chunk")
                    
                    all_chunks.extend(chunks)
                    all_metadata.extend(metadata)
                    
                    # Mark as indexed
                    resource.indexed = True
                    debug_content.append(f"✅ Successfully processed {resource.filename}")
                    
                except Exception as e:
                    debug_content.append(f"❌ Error processing {resource.filename}: {str(e)}")
                    import traceback
                    debug_content.append(f"   Traceback: {traceback.format_exc()}")
            else:
                debug_content.append(f"❌ File not found: {resource.file_path}")
        
        debug_content.append(f"\n--- INDEXING SUMMARY ---")
        debug_content.append(f"📊 Total chunks: {len(all_chunks)}")
        debug_content.append(f"📊 Total metadata entries: {len(all_metadata)}")
        
        if all_chunks:
            # Build/update index
            debug_content.append(f"🔨 Building/updating FAISS index...")
            em = get_embeddings_manager()
            
            if force_reindex:
                em.build_index(all_chunks, all_metadata)
                debug_content.append(f"✅ Built new index from scratch")
            else:
                em.add_documents(all_chunks, all_metadata)
                debug_content.append(f"✅ Added documents to existing index")

            db.session.commit()
            
            # Final verification
            stats = em.get_stats()
            debug_content.append(f"\n--- FINAL INDEX STATS ---")
            debug_content.append(f"📊 Total documents in index: {stats['total_documents']}")
            debug_content.append(f"📊 Index loaded: {stats['index_loaded']}")
            debug_content.append(f"📊 Model loaded: {stats['model_loaded']}")
            
            # Write debug file
            debug_content.append(f"\n✅ INDEXING COMPLETED SUCCESSFULLY!")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_content))
            
            return jsonify({
                'message': f'Successfully indexed {len(pdf_resources)} PDFs',
                'count': len(pdf_resources),
                'chunks': len(all_chunks),
                'debug_file': debug_file,
                'stats': stats
            })
        else:
            debug_content.append(f"❌ No content extracted from PDFs")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_content))
            return jsonify({'message': 'No content extracted from PDFs', 'count': 0, 'debug_file': debug_file})
    
    except Exception as e:
        error_msg = f"❌ Indexing failed: {str(e)}"
        import traceback
        full_error = traceback.format_exc()
        
        # Write error to debug file
        try:
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{error_msg}\n{full_error}")
        except:
            pass
            
        return jsonify({'error': error_msg, 'debug_file': debug_file if 'debug_file' in locals() else None}), 500

# ==================== QUIZZES API ====================

def _quiz_to_dict(q):
    return {
        'id': q.id, 'title': q.title, 'description': q.description,
        'category': q.category, 'difficulty': q.difficulty,
        'questions': q.questions or [],
        'question_count': len(q.questions) if q.questions else 0,
        'created_at': q.created_at.isoformat(),
    }


@app.route('/api/quizzes')
def api_quizzes():
    """List quizzes (public — students see this)."""
    category = request.args.get('category', '')
    query = Quiz.query
    if category:
        query = query.filter_by(category=category)
    quizzes_list = query.order_by(Quiz.created_at.desc()).all()
    categories = [c[0] for c in db.session.query(Quiz.category).distinct().all() if c[0]]
    return jsonify({
        'quizzes': [_quiz_to_dict(q) for q in quizzes_list],
        'categories': categories,
    })


@app.route('/api/quiz/<int:quiz_id>')
def api_get_quiz(quiz_id):
    """Get quiz questions WITHOUT correct answers (for students taking the quiz)."""
    quiz = Quiz.query.get_or_404(quiz_id)
    safe = []
    for q in (quiz.questions or []):
        safe.append({
            'id':             q.get('id'),
            'question':       q.get('question', ''),
            'optionA':        q.get('optionA', (q.get('options') or ['','','',''])[0]),
            'optionB':        q.get('optionB', (q.get('options') or ['','','',''])[1]),
            'optionC':        q.get('optionC', (q.get('options') or ['','','',''])[2]),
            'optionD':        q.get('optionD', (q.get('options') or ['','','',''])[3]),
            'topic':          q.get('topic', ''),
            'sourceDocument': q.get('sourceDocument', ''),
        })
    return jsonify({
        'id': quiz.id, 'title': quiz.title, 'description': quiz.description,
        'category': quiz.category, 'difficulty': quiz.difficulty,
        'questions': safe, 'total_questions': len(safe),
    })


@app.route('/api/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    """Submit quiz answers and calculate score (student)."""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    answers = data.get('answers', {})

    correct = 0
    total = len(quiz.questions) if quiz.questions else 0
    detail = []

    for question in (quiz.questions or []):
        q_id = str(question.get('id', ''))
        user_ans = answers.get(q_id)

        # support both new MCQ format and legacy index format
        correct_ans = question.get('correctAnswer')
        if not correct_ans and 'correct_answer' in question:
            idx = question['correct_answer']
            if isinstance(idx, int) and 0 <= idx <= 3:
                correct_ans = ['A', 'B', 'C', 'D'][idx]

        is_correct = bool(user_ans and correct_ans and user_ans == correct_ans)
        if is_correct:
            correct += 1

        opts = question.get('options') or []
        detail.append({
            'question_id':   q_id,
            'question':      question.get('question', ''),
            'user_answer':   user_ans,
            'correct_answer': correct_ans,
            'is_correct':    is_correct,
            'optionA': question.get('optionA') or (opts[0] if len(opts) > 0 else ''),
            'optionB': question.get('optionB') or (opts[1] if len(opts) > 1 else ''),
            'optionC': question.get('optionC') or (opts[2] if len(opts) > 2 else ''),
            'optionD': question.get('optionD') or (opts[3] if len(opts) > 3 else ''),
        })

    score = (correct / total) * 100 if total > 0 else 0

    if 'user_id' in session:
        result = QuizResult(
            user_id=session['user_id'],
            quiz_id=quiz_id,
            score=score,
            total_questions=total,
            answers=answers,
        )
        db.session.add(result)
        db.session.commit()

    return jsonify({
        'score': score, 'correct': correct, 'total': total,
        'percentage': round(score, 2), 'results': detail,
    })


@app.route('/api/quiz-results')
@require_login
def api_quiz_results():
    """Get quiz results for logged-in user."""
    results = QuizResult.query.filter_by(user_id=session['user_id']).order_by(QuizResult.completed_at.desc()).all()
    return jsonify({
        'results': [
            {
                'id': r.id, 'quiz_id': r.quiz_id,
                'quiz_title': r.quiz.title if r.quiz else 'Unknown',
                'score': r.score, 'total_questions': r.total_questions,
                'completed_at': r.completed_at.isoformat(),
            }
            for r in results
        ]
    })


# ---------- ADMIN-ONLY quiz endpoints ----------

@app.route('/api/quiz/topics')
def api_quiz_topics():
    """Return quiz generation status (LLM-based, no sources needed)."""
    llm_ready = quiz_generator._chatbot is not None
    return jsonify({'llm_ready': llm_ready})


@app.route('/api/quiz/generate', methods=['POST'])
@require_admin
def api_generate_quiz():
    """Generate MCQ quiz using the local LLM (admin only)."""
    try:
        data = request.get_json() or {}
        num_questions = min(int(data.get('num_questions', 10)), 20)
        title      = data.get('title', 'Auto-Generated Quiz')
        category   = data.get('category', 'General')
        difficulty = data.get('difficulty', 'medium')
        topic      = data.get('topic', category)

        # Ensure chatbot is wired up (in case preload hasn't finished)
        if quiz_generator._chatbot is None:
            try:
                bot = get_chatbot()
                quiz_generator.set_chatbot(bot)
            except Exception:
                pass

        questions = quiz_generator.generate_quiz(
            topic=topic, num_questions=num_questions, difficulty=difficulty,
        )

        quiz = Quiz(
            title=title,
            description=f"AI-generated quiz on {topic} ({len(questions)} questions)",
            category=category, difficulty=difficulty,
            questions=questions,
        )
        db.session.add(quiz)
        db.session.commit()

        return jsonify({
            'success': True, 'quiz_id': quiz.id, 'title': quiz.title,
            'num_questions': len(questions), 'questions': questions,
        })
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': f'Quiz generation failed: {e}'}), 500


@app.route('/api/quiz/create', methods=['POST'])
@require_admin
def api_create_quiz():
    """Manually create a quiz with admin-provided questions."""
    data = request.get_json() or {}
    title    = data.get('title', 'New Quiz')
    category = data.get('category', 'General')
    difficulty = data.get('difficulty', 'medium')
    description = data.get('description', '')
    raw_questions = data.get('questions', [])

    storage = []
    for i, q in enumerate(raw_questions):
        ca = q.get('correctAnswer', 'A')
        entry = {
            'id': i + 1,
            'question':       q.get('question', ''),
            'optionA':        q.get('optionA', ''),
            'optionB':        q.get('optionB', ''),
            'optionC':        q.get('optionC', ''),
            'optionD':        q.get('optionD', ''),
            'correctAnswer':  ca,
            'topic':          q.get('topic', category),
            'sourceDocument': q.get('sourceDocument', 'Manual'),
            'options': [q.get('optionA',''), q.get('optionB',''), q.get('optionC',''), q.get('optionD','')],
            'correct_answer': ['A','B','C','D'].index(ca) if ca in ('A','B','C','D') else 0,
        }
        storage.append(entry)

    quiz = Quiz(title=title, description=description, category=category,
                difficulty=difficulty, questions=storage)
    db.session.add(quiz)
    db.session.commit()
    return jsonify({'success': True, 'quiz_id': quiz.id, 'title': quiz.title}), 201


@app.route('/api/quiz/<int:quiz_id>/edit', methods=['PUT'])
@require_admin
def api_edit_quiz(quiz_id):
    """Edit quiz metadata and/or replace all questions."""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json() or {}

    if 'title' in data:       quiz.title = data['title']
    if 'description' in data: quiz.description = data['description']
    if 'category' in data:    quiz.category = data['category']
    if 'difficulty' in data:  quiz.difficulty = data['difficulty']

    if 'questions' in data:
        storage = []
        for i, q in enumerate(data['questions']):
            ca = q.get('correctAnswer', 'A')
            entry = {
                'id':             q.get('id', i + 1),
                'question':       q.get('question', ''),
                'optionA':        q.get('optionA', ''),
                'optionB':        q.get('optionB', ''),
                'optionC':        q.get('optionC', ''),
                'optionD':        q.get('optionD', ''),
                'correctAnswer':  ca,
                'topic':          q.get('topic', quiz.category),
                'sourceDocument': q.get('sourceDocument', ''),
                'options': [q.get('optionA',''), q.get('optionB',''), q.get('optionC',''), q.get('optionD','')],
                'correct_answer': ['A','B','C','D'].index(ca) if ca in ('A','B','C','D') else 0,
            }
            storage.append(entry)
        quiz.questions = storage

    db.session.commit()
    return jsonify({'success': True, 'quiz': _quiz_to_dict(quiz)})


@app.route('/api/quiz/<int:quiz_id>/question', methods=['POST'])
@require_admin
def api_add_question(quiz_id):
    """Add a single question to an existing quiz."""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json() or {}
    questions = list(quiz.questions or [])
    next_id = max((q.get('id', 0) for q in questions), default=0) + 1
    ca = data.get('correctAnswer', 'A')
    entry = {
        'id': next_id,
        'question':       data.get('question', ''),
        'optionA':        data.get('optionA', ''),
        'optionB':        data.get('optionB', ''),
        'optionC':        data.get('optionC', ''),
        'optionD':        data.get('optionD', ''),
        'correctAnswer':  ca,
        'topic':          data.get('topic', quiz.category),
        'sourceDocument': data.get('sourceDocument', 'Manual'),
        'options': [data.get('optionA',''), data.get('optionB',''), data.get('optionC',''), data.get('optionD','')],
        'correct_answer': ['A','B','C','D'].index(ca) if ca in ('A','B','C','D') else 0,
    }
    questions.append(entry)
    quiz.questions = questions
    db.session.commit()
    return jsonify({'success': True, 'question': entry, 'total': len(questions)}), 201


@app.route('/api/quiz/<int:quiz_id>/question/<int:question_id>', methods=['PUT'])
@require_admin
def api_edit_question(quiz_id, question_id):
    """Edit a single question inside a quiz."""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json() or {}
    questions = list(quiz.questions or [])
    found = False
    for q in questions:
        if q.get('id') == question_id:
            for field in ('question', 'optionA', 'optionB', 'optionC', 'optionD',
                          'correctAnswer', 'topic', 'sourceDocument'):
                if field in data:
                    q[field] = data[field]
            q['options'] = [q['optionA'], q['optionB'], q['optionC'], q['optionD']]
            q['correct_answer'] = ['A','B','C','D'].index(q['correctAnswer']) if q['correctAnswer'] in ('A','B','C','D') else 0
            found = True
            break
    if not found:
        return jsonify({'error': 'Question not found'}), 404
    quiz.questions = questions
    db.session.commit()
    return jsonify({'success': True, 'questions': questions})


@app.route('/api/quiz/<int:quiz_id>/question/<int:question_id>', methods=['DELETE'])
@require_admin
def api_delete_question(quiz_id, question_id):
    """Delete a single question from a quiz."""
    quiz = Quiz.query.get_or_404(quiz_id)
    old_len = len(quiz.questions or [])
    questions = [q for q in (quiz.questions or []) if q.get('id') != question_id]
    if len(questions) == old_len:
        return jsonify({'error': 'Question not found'}), 404
    quiz.questions = questions
    db.session.commit()
    return jsonify({'success': True, 'remaining': len(questions)})


@app.route('/api/quiz/<int:quiz_id>/delete', methods=['DELETE'])
@require_admin
def api_delete_quiz(quiz_id):
    """Delete an entire quiz and its results."""
    quiz = Quiz.query.get_or_404(quiz_id)
    QuizResult.query.filter_by(quiz_id=quiz_id).delete()
    db.session.delete(quiz)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Quiz deleted'})


@app.route('/api/quiz/<int:quiz_id>/admin')
@require_admin
def api_quiz_admin_detail(quiz_id):
    """Get full quiz detail INCLUDING correct answers (admin only)."""
    quiz = Quiz.query.get_or_404(quiz_id)
    return jsonify(_quiz_to_dict(quiz))


@app.route('/api/quiz/<int:quiz_id>/analytics')
@require_admin
def api_quiz_analytics(quiz_id):
    """Analytics for a single quiz (admin only)."""
    quiz = Quiz.query.get_or_404(quiz_id)
    results = QuizResult.query.filter_by(quiz_id=quiz_id).all()

    if not results:
        return jsonify({
            'quiz_id': quiz_id, 'title': quiz.title,
            'attempts': 0, 'average_score': 0, 'highest_score': 0,
            'lowest_score': 0, 'pass_count': 0, 'fail_count': 0,
            'question_accuracy': [],
        })

    scores = [r.score for r in results]
    pass_threshold = 50.0
    pass_count = sum(1 for s in scores if s >= pass_threshold)

    # question-wise accuracy
    question_correct = {}
    question_total   = {}
    for r in results:
        ans = r.answers or {}
        for q in (quiz.questions or []):
            qid = str(q.get('id', ''))
            question_total[qid] = question_total.get(qid, 0) + 1
            user_ans = ans.get(qid)
            ca = q.get('correctAnswer')
            if not ca and 'correct_answer' in q:
                idx = q['correct_answer']
                if isinstance(idx, int) and 0 <= idx <= 3:
                    ca = ['A','B','C','D'][idx]
            if user_ans and ca and user_ans == ca:
                question_correct[qid] = question_correct.get(qid, 0) + 1

    q_accuracy = []
    for q in (quiz.questions or []):
        qid = str(q.get('id', ''))
        t = question_total.get(qid, 0)
        c = question_correct.get(qid, 0)
        q_accuracy.append({
            'question_id': qid,
            'question': q.get('question', '')[:120],
            'attempts': t, 'correct': c,
            'accuracy': round((c / t) * 100, 1) if t > 0 else 0,
        })

    return jsonify({
        'quiz_id': quiz_id, 'title': quiz.title,
        'attempts': len(results),
        'average_score': round(sum(scores) / len(scores), 2),
        'highest_score': round(max(scores), 2),
        'lowest_score':  round(min(scores), 2),
        'pass_count': pass_count,
        'fail_count': len(results) - pass_count,
        'question_accuracy': q_accuracy,
    })


@app.route('/api/quiz/status')
def api_quiz_status():
    """Check if LLM-based quiz generation is available."""
    llm_ready = quiz_generator._chatbot is not None
    return jsonify({
        'ready': llm_ready,
        'llm_status': 'loaded' if llm_ready else 'not loaded',
    })

# ==================== ADMIN API ====================

@app.route('/api/admin/dashboard')
def api_admin_dashboard():
    """Get admin dashboard data"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    # System info
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Stats
    total_users = User.query.count()
    total_resources = Resource.query.count()
    total_quizzes = Quiz.query.count()
    total_chats = ChatHistory.query.count()
    recent_chat = ChatHistory.query.order_by(ChatHistory.created_at.desc()).limit(10).all()
    
    return jsonify({
        'system_info': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': disk.percent,
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2)
        },
        'stats': {
            'total_users': total_users,
            'total_resources': total_resources,
            'total_quizzes': total_quizzes,
            'total_chats': total_chats
        },
        'recent_chat': [
            {
                'id': c.id,
                'question': c.question,
                'answer': c.answer[:100] + '...' if len(c.answer) > 100 else c.answer,
                'created_at': c.created_at.isoformat()
            }
            for c in recent_chat
        ]
    })

@app.route('/api/admin/upload', methods=['POST'])
def api_upload_file():
    """Upload a new resource"""
    # Debug: Check session
    print(f"📤 Upload request from: {request.remote_addr}")
    print(f"   Session data: {dict(session)}")
    print(f"   User in session: {'user_id' in session}")
    
    if 'user_id' not in session:
        print(f"❌ Upload rejected: No session found")
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        print(f"❌ Upload rejected: User not admin - User: {user}, Is Admin: {user.is_admin if user else 'N/A'}")
        return jsonify({'error': 'Admin access required'}), 403
    
    print(f"✅ Upload authorized for user: {user.username}")
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    title = request.form.get('title', '')
    description = request.form.get('description', '')
    category = request.form.get('category', '')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    filename = secure_filename(file.filename)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Save file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Determine file type
    file_ext = filename.rsplit('.', 1)[1].lower()
    file_type = file_ext
    
    # Create resource entry
    resource = Resource(
        title=title or filename,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        file_size=get_file_size(file_path),
        description=description,
        category=category
    )
    db.session.add(resource)
    db.session.commit()
    
    return jsonify({
        'message': 'File uploaded successfully',
        'resource': resource.to_dict()
    })

@app.route('/api/admin/resource/<int:resource_id>/delete', methods=['DELETE'])
def api_delete_resource(resource_id):
    """Delete a resource"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    resource = Resource.query.get_or_404(resource_id)
    
    # Delete file
    if os.path.exists(resource.file_path):
        os.remove(resource.file_path)
    
    # Delete database entry
    db.session.delete(resource)
    db.session.commit()
    
    return jsonify({'message': 'Resource deleted successfully'})

# ==================== CONVERSATION API ====================

@app.route('/api/conversations')
def api_conversations():
    """Get user's conversations"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from database.models import Conversation
    conversations = Conversation.query.filter_by(
        user_id=session['user_id']
    ).order_by(Conversation.updated_at.desc()).all()
    
    return jsonify({
        'conversations': [c.to_dict() for c in conversations]
    })

@app.route('/api/conversations', methods=['POST'])
def api_create_conversation():
    """Create new conversation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from database.models import Conversation
    data = request.json
    conversation = Conversation(
        user_id=session['user_id'],
        title=data.get('title', 'New Conversation')
    )
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify(conversation.to_dict()), 201

@app.route('/api/conversations/<int:conv_id>/messages')
def api_conversation_messages(conv_id):
    """Get messages in a conversation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from database.models import Conversation
    conversation = Conversation.query.get_or_404(conv_id)
    if conversation.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    messages = ChatHistory.query.filter_by(
        conversation_id=conv_id
    ).order_by(ChatHistory.created_at.asc()).all()
    
    return jsonify({
        'messages': [m.to_dict() for m in messages]
    })

@app.route('/api/conversations/<int:conv_id>', methods=['DELETE'])
def api_delete_conversation(conv_id):
    """Delete a conversation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from database.models import Conversation
    conversation = Conversation.query.get_or_404(conv_id)
    if conversation.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(conversation)
    db.session.commit()
    
    return jsonify({'message': 'Conversation deleted'}), 200

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    # For API routes, return JSON
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    # For frontend routes, serve React app (it handles 404s)
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== RUN APP ====================

if __name__ == '__main__':
    # Ensure necessary directories exist
    os.makedirs(app.config['RESOURCES_PATH'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MODELS_PATH'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['FAISS_INDEX_PATH']), exist_ok=True)
    
    # Check if production build exists
    build_exists = os.path.exists(os.path.join(app.static_folder, 'assets'))
    mode = "PRODUCTION" if build_exists else "DEVELOPMENT (API ONLY)"
    
    print(f"""
    ╔════════════════════════════════════════════════════════╗
    ║   🎓 Offline AI-Powered Learning Hub - BACKEND        ║
    ║   Mode: {mode:<43} ║
    ║   API Server: http://127.0.0.1:5000                   ║
    ║                                                        ║""")
    
    if build_exists:
        print(f"""    ║   Access App: http://127.0.0.1:5000                   ║""")
    else:
        print(f"""    ║   ⚠️  React dev server required!                      ║
    ║   Run: cd frontend && npm run dev                     ║
    ║   Then open: http://localhost:3000                    ║""")
    
    print(f"""    ║                                                        ║
    ║   Admin Login: admin / admin123                       ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # 🚀 MODELS WILL LOAD ON FIRST USE (lazy loading for compatibility)

    # Run server on 0.0.0.0 to accept connections from network (mobile devices)
    app.run(host='0.0.0.0', port=5000, debug=False)
