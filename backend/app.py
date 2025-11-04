from flask import Flask, request, jsonify, session, send_file, send_from_directory
from flask_cors import CORS
from flask_compress import Compress
from werkzeug.utils import secure_filename
import os
import psutil
from datetime import datetime
from functools import wraps
from config import config
from database.models import db, User, Resource, Quiz, QuizResult, Notification, ChatHistory
from database.init_db import init_database, seed_sample_resources
from ai.embeddings import EmbeddingsManager
from ai.pdf_processor import process_pdf_for_embeddings, process_directory_for_embeddings
from ai.chatbot import ChatBot

# Initialize Flask app
app = Flask(__name__, static_folder='static/dist', static_url_path='')

# Load configuration based on environment
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])
config[env].init_app(app)

# Enable response compression for faster API responses
Compress(app)

# Enable CORS for React frontend with session support
CORS(app, 
     supports_credentials=True,
     origins=app.config['CORS_ORIGINS'],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
)

# Initialize database
db.init_app(app)

# Initialize AI components (lazy loading)
embeddings_manager = None
chatbot = None

def get_embeddings_manager():
    """Lazy load embeddings manager"""
    global embeddings_manager
    if embeddings_manager is None:
        embeddings_manager = EmbeddingsManager(
            model_name=app.config['EMBEDDINGS_MODEL'],
            index_path=app.config['FAISS_INDEX_PATH'],
            metadata_path=app.config['EMBEDDINGS_CACHE_PATH']
        )
    return embeddings_manager

def get_chatbot():
    """Lazy load chatbot"""
    global chatbot
    if chatbot is None:
        chatbot = ChatBot(
            model_name=app.config['GPT4ALL_MODEL'],
            model_path=app.config['MODELS_PATH']
        )
    return chatbot

# Initialize database on first run
with app.app_context():
    init_database(app)
    seed_sample_resources(app)

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
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        session.permanent = True
        
        user.last_login = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin
            }
        })
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
    """Download a resource"""
    resource = Resource.query.get_or_404(resource_id)
    
    if os.path.exists(resource.file_path):
        return send_file(resource.file_path, as_attachment=True, download_name=resource.filename)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/resources/<int:resource_id>/download')
def api_resource_download(resource_id):
    """Alternative download endpoint"""
    resource = Resource.query.get_or_404(resource_id)
    
    if os.path.exists(resource.file_path):
        return send_file(resource.file_path, as_attachment=True, download_name=resource.filename)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/resources/<int:resource_id>/view')
def api_resource_view(resource_id):
    """View a resource inline (for PDFs)"""
    resource = Resource.query.get_or_404(resource_id)
    
    if os.path.exists(resource.file_path):
        # Determine mimetype
        mimetype = 'application/pdf' if resource.file_type == 'pdf' else 'application/octet-stream'
        
        # Send file with inline disposition for viewing in browser
        return send_file(
            resource.file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=resource.filename
        )
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Optimized chat endpoint with caching"""
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    try:
        # Get embeddings manager and search for relevant context
        em = get_embeddings_manager()
        search_results = em.search(question, top_k=5)
        
        # Get chatbot and generate response (uses internal caching)
        bot = get_chatbot()
        result = bot.chat_with_context(question, search_results)
        
        # Save chat history asynchronously (non-blocking)
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
            
            # Update conversation timestamp
            if conversation_id:
                from database.models import Conversation
                conversation = Conversation.query.get(conversation_id)
                if conversation:
                    conversation.updated_at = datetime.now()
            
            db.session.commit()
        
        return jsonify({
            'answer': result['answer'],
            'sources': result.get('sources', []),
            'context_used': result.get('context_used', False),
            'generation_time': result.get('generation_time', 0),
            'total_time': result.get('total_time', 0)
        })
    
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return jsonify({
            'answer': "I apologize, but I encountered an error. Please try again.",
            'error': str(e) if app.debug else "Internal error"
        }), 500

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
                    # Extract text with our fixed processor
                    from ai.pdf_processor import extract_text_from_pdf
                    raw_text = extract_text_from_pdf(resource.file_path)
                    
                    debug_content.append(f"📝 Raw text length: {len(raw_text)} characters")
                    debug_content.append(f"📝 First 200 chars: {repr(raw_text[:200])}")
                    
                    # Calculate readability
                    words = raw_text.split()
                    if words:
                        readable_words = sum(1 for word in words if word.isalpha() and len(word) > 1)
                        readability = readable_words / len(words)
                        debug_content.append(f"📊 Readability score: {readability:.3f} ({readable_words}/{len(words)} words)")
                    
                    # Process into chunks
                    chunks, metadata = process_pdf_for_embeddings(resource.file_path)
                    
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

@app.route('/api/quizzes')
def api_quizzes():
    """Get quizzes list"""
    category = request.args.get('category', '')
    
    query = Quiz.query
    if category:
        query = query.filter_by(category=category)
    
    quizzes_list = query.order_by(Quiz.created_at.desc()).all()
    categories = db.session.query(Quiz.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return jsonify({
        'quizzes': [
            {
                'id': q.id,
                'title': q.title,
                'description': q.description,
                'category': q.category,
                'difficulty': q.difficulty,
                'questions': q.questions,
                'created_at': q.created_at.isoformat()
            }
            for q in quizzes_list
        ],
        'categories': categories
    })

@app.route('/api/quiz/<int:quiz_id>')
def api_get_quiz(quiz_id):
    """Get a specific quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    return jsonify({
        'id': quiz.id,
        'title': quiz.title,
        'description': quiz.description,
        'category': quiz.category,
        'difficulty': quiz.difficulty,
        'questions': quiz.questions
    })

@app.route('/api/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    """Submit quiz answers"""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    answers = data.get('answers', {})
    
    # Calculate score
    correct = 0
    total = len(quiz.questions)
    
    for question in quiz.questions:
        q_id = str(question['id'])
        if q_id in answers and int(answers[q_id]) == question['correct_answer']:
            correct += 1
    
    score = (correct / total) * 100 if total > 0 else 0
    
    # Save result if user is logged in
    if 'user_id' in session:
        result = QuizResult(
            user_id=session['user_id'],
            quiz_id=quiz_id,
            score=score,
            total_questions=total,
            answers=answers
        )
        db.session.add(result)
        db.session.commit()
    
    return jsonify({
        'score': score,
        'correct': correct,
        'total': total,
        'percentage': round(score, 2)
    })

@app.route('/api/quiz-results')
def api_quiz_results():
    """Get quiz results for logged in user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    results = QuizResult.query.filter_by(user_id=session['user_id']).order_by(QuizResult.completed_at.desc()).all()
    return jsonify({
        'results': [
            {
                'id': r.id,
                'quiz_id': r.quiz_id,
                'quiz_title': r.quiz.title if r.quiz else 'Unknown',
                'score': r.score,
                'total_questions': r.total_questions,
                'completed_at': r.completed_at.isoformat()
            }
            for r in results
        ]
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
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
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
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
    print("\n✅ Backend ready! AI models will load on first query.\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
