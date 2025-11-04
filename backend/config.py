import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Flask - Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-please-change')
    
    # Warn if using default secret key in production
    if SECRET_KEY == 'dev-secret-key-please-change' and os.getenv('FLASK_ENV') == 'production':
        print("⚠️  WARNING: Using default SECRET_KEY in production! Please change it in .env")
    
    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'learning_hub.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Admin Credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # Warn if using default admin password
    if ADMIN_PASSWORD == 'admin123':
        print("⚠️  WARNING: Using default admin password! Please change it in .env")
    
    # AI Models - Using TinyLlama 1.1B for FAST responses (5-8x faster than Orca)
    # Alternative models: 'orca-mini-3b-gguf2-q4_0.gguf' (slower but better quality)
    GPT4ALL_MODEL = os.getenv('GPT4ALL_MODEL', 'tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf')
    EMBEDDINGS_MODEL = os.getenv('EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2')
    
    # Paths
    RESOURCES_PATH = os.path.join(BASE_DIR, os.getenv('RESOURCES_PATH', 'resources'))
    MODELS_PATH = os.path.join(BASE_DIR, os.getenv('MODELS_PATH', 'models'))
    UPLOAD_FOLDER = os.path.join(RESOURCES_PATH, 'uploads')
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'ppt', 'pptx', 'doc', 'docx', 'txt', 'mp4', 'avi', 'mkv'}
    
    # AI Settings
    FAISS_INDEX_PATH = os.path.join(BASE_DIR, 'embeddings_cache', 'faiss_index.bin')
    EMBEDDINGS_CACHE_PATH = os.path.join(BASE_DIR, 'embeddings_cache', 'embeddings.pkl')
    
    # Performance
    MAX_SEARCH_RESULTS = 5
    CHUNK_SIZE = 500  # Characters per chunk for embedding
    CHUNK_OVERLAP = 50
    
    # CORS Configuration - Allow network access from local IP
    # For production, update CORS_ORIGINS environment variable with your specific origins
    default_origins = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://10.50.173.74:3000,http://10.50.173.74:3001,http://10.50.173.74:5173'
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', default_origins).split(',')
    
    # Flask Environment
    DEBUG = os.getenv('FLASK_ENV', 'development') != 'production'
    TESTING = False
    
    @staticmethod
    def init_app(app):
        """Initialize application"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to file in production
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/learning_hub.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Learning Hub startup')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
