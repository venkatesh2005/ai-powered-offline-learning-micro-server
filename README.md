# 🎓 AI Learning Hub - Offline Education Platform

A modern, offline-first learning platform powered by AI, built with React, Flask, and GPT4All.

## ✨ Features

- 🤖 **AI-Powered Chat** - Interact with AI models running completely offline
- 📚 **Resource Management** - Upload and manage PDFs, videos, and documents
- 🧠 **Interactive Quizzes** - Test your knowledge with adaptive quizzes
- 🔍 **Smart Search** - FAISS-powered semantic search across your resources
- 🎨 **Modern UI** - Beautiful React + Tailwind CSS interface
- 🔒 **100% Offline** - No internet required, complete privacy
- 👥 **Multi-user Support** - Separate student and admin accounts

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.9-3.11** (Python 3.12+ may have compatibility issues)
- **Node.js 18+** and npm
- **4GB+ RAM** (for AI model inference)
- **10GB+ disk space** (for models and resources)
- Windows, Linux, or macOS

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Final-Year-Project

# Backend Setup
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
# source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file and configure
copy .env.example .env
# Edit .env with your settings (SECRET_KEY, ADMIN credentials, etc.)

# Initialize database
python -c "from database.init_db import init_database; from app import app; import sys; sys.path.insert(0, '.'); with app.app_context(): init_database(app)"

cd ..

# Frontend Setup
cd frontend
npm install
cd ..
```

### 3. Run the Application

**Development Mode** (Recommended for development):

```bash
# Terminal 1 - Backend
cd backend
..\venv\Scripts\activate  # Windows (venv\Scripts\activate)
python app.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

**Production Mode**:

```bash
# Build frontend for production
cd frontend
npm run build

# The built files will be in backend/static/dist/
# Run backend only - it will serve the React app
cd ../backend
..\venv\Scripts\activate
python app.py

# Access at http://localhost:5000
```

### 4. Access the Application

- **Frontend (Development):** http://localhost:3000
- **Frontend (Production):** http://localhost:5000
- **Backend API:** http://localhost:5000/api
- **Default Admin Login:** `admin` / `admin123`

> ⚠️ **Important:** Change the default admin password in production!

## 📁 Project Structure

```
Final-Year-Project/
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # Reusable components (Navbar, etc.)
│   │   ├── pages/             # Page components (Home, Chat, Resources, etc.)
│   │   ├── App.jsx            # Main app with routing
│   │   ├── main.jsx           # Entry point
│   │   └── index.css          # Tailwind CSS styles
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── backend/                    # Flask Backend
│   ├── ai/                    # AI modules
│   │   ├── chatbot.py         # GPT4All integration
│   │   ├── embeddings.py      # FAISS embeddings
│   │   └── pdf_processor.py   # PDF text extraction
│   ├── database/              # Database models
│   │   ├── models.py          # SQLAlchemy models
│   │   └── init_db.py         # Database initialization
│   ├── models/                # AI model files (.gguf)
│   ├── resources/             # Uploaded resources
│   ├── embeddings_cache/      # FAISS index cache
│   ├── instance/              # SQLite database
│   ├── docs/                  # Documentation
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration
│   ├── .env                   # Environment variables
│   └── requirements.txt       # Python dependencies
│
├── venv/                       # Python virtual environment
├── start.bat                   # Startup script
└── README.md                   # This file
```

## 🛠️ Technology Stack

### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Framer Motion** - Animation library
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Lucide React** - Icon library

### Backend
- **Flask 3.0** - Web framework
- **SQLAlchemy 3.1** - ORM
- **GPT4All 2.8** - Local LLM (Mistral 7B)
- **FAISS** - Vector similarity search
- **Sentence Transformers** - Text embeddings
- **PyPDF2 & pdfplumber** - PDF processing
- **Python-dotenv** - Environment management

## 📖 Usage Guide

### Uploading Resources

1. Navigate to the **Resources** page
2. Click "Upload New Resource"
3. Select your PDF, video, or document
4. The file will be automatically processed and indexed

### Using AI Chat

1. Go to the **Chat** page
2. Type your question about the uploaded resources
3. The AI will search through your materials and provide contextual answers
4. Sources are displayed with each response

### Creating Quizzes

1. Visit the **Quizzes** page
2. Browse available quizzes or create new ones
3. Take quizzes and track your progress
4. View results and performance analytics

### Admin Dashboard

1. Login with admin credentials
2. Access the **Admin** page
3. View system statistics
4. Index new resources for AI search
5. Monitor system performance

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory (copy from `.env.example`):

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-in-production

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# AI Models
GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# Paths (relative to backend/)
MODELS_PATH=models
RESOURCES_PATH=resources
```

### Security Recommendations

For production deployment:

1. **Change SECRET_KEY**: Generate a strong random key
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Change Admin Password**: Update `ADMIN_PASSWORD` in `.env`

3. **Use Password Hashing**: The current implementation stores passwords in plaintext. For production, implement proper password hashing (e.g., bcrypt, werkzeug.security)

4. **Enable HTTPS**: Use a reverse proxy (nginx, Apache) with SSL/TLS certificates

5. **Set CORS properly**: Update CORS origins in `app.py` to match your domain

6. **Database**: Consider using PostgreSQL or MySQL for production instead of SQLite

## 🤖 AI Model

The platform uses **Orca Mini 3B** by default (1.9GB) which downloads automatically on first use. Models are cached in `backend/models/` for offline use.

### Alternative Models

You can use other GPT4All-compatible models:

**Desktop (Best Quality, 4-8 GB RAM):**
- Mistral 7B Instruct (4.1 GB): `mistral-7b-instruct-v0.1.Q4_0.gguf`
- GPT4All Falcon (3.9 GB): `gpt4all-falcon-q4_0.gguf`

**Raspberry Pi / Low RAM (2-4 GB RAM):**
- Orca Mini 3B (1.9 GB): `orca-mini-3b-gguf2-q4_0.gguf` ✅ Default
- GPT4All-J (3.5 GB): `ggml-gpt4all-j-v1.3-groovy.bin`

To change models:
1. Download a `.gguf` model from [GPT4All Models](https://gpt4all.io/models/)
2. Place it in `backend/models/`
3. Update `GPT4ALL_MODEL` in `.env`

## � Production Deployment

### Building for Production

```bash
# Build frontend
cd frontend
npm run build

# The build output is automatically placed in backend/static/dist/

# Run backend in production mode
cd ../backend
python app.py
```

### Deployment Options

**Option 1: Traditional Server (VPS, Dedicated Server)**
- Use gunicorn or waitress as WSGI server
- Set up nginx as reverse proxy
- Configure SSL/TLS certificates
- Set up systemd service for auto-restart

**Option 2: Docker**
- Create Dockerfile for containerization
- Use docker-compose for multi-container setup
- Easy scaling and deployment

**Option 3: Platform as a Service**
- Deploy to platforms like Railway, Render, or Heroku
- Note: AI models are large (2-4GB), ensure sufficient storage

### Production Checklist

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Change admin password
- [ ] Implement password hashing
- [ ] Set up HTTPS/SSL
- [ ] Configure CORS for your domain
- [ ] Set up database backups
- [ ] Configure logging and monitoring
- [ ] Set up error tracking (e.g., Sentry)
- [ ] Optimize model size for your hardware
- [ ] Test on production-like environment
- [ ] Set up CI/CD pipeline

## 🐛 Troubleshooting

### AI Model Not Loading
- Ensure you have ~4GB free disk space
- Check internet connection for first-time download
- Verify `backend/models/` directory exists
- Check model file isn't corrupted

### Database Errors
- Delete `backend/instance/learning_hub.db` to reset
- Reinitialize: Run the database init command from Installation step

### Port Already in Use
- **Backend**: Change port in `backend/app.py` (default: 5000)
- **Frontend**: Change port in `frontend/vite.config.js` (default: 3000)

### Import/Module Errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r backend/requirements.txt`
- Clear Python cache: Delete all `__pycache__` directories

### Frontend Build Errors
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Clear npm cache: `npm cache clean --force`

### AI Responses Too Slow
- Use a smaller model (Orca Mini 3B)
- Reduce `max_tokens` in `backend/ai/chatbot.py`
- Ensure no other heavy processes are running
- Consider using a machine with better CPU

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ for offline education**
