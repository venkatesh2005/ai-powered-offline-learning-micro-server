# 🎓 AI Learning Hub - Setup Instructions

## 📋 Prerequisites
- Python 3.9-3.13
- Node.js 16+
- 4GB+ RAM
- 10GB+ free disk space

## 🚀 Quick Setup

### 1. Backend Setup (Python)
```bash
# Navigate to project root
cd Final-Year-Project

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 2. Frontend Setup (React)
```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install
```

## 🎮 Running the Application

### Start Backend (Terminal 1)
```bash
cd backend
# Activate venv first (if not already active)
python app.py
```
Backend will run on: `http://127.0.0.1:5000`

### Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```
Frontend will run on: `http://localhost:3000`

## 🔐 Default Login
- **Username:** admin
- **Password:** admin123

## 📦 What's Included
- ✅ Optimized AI chatbot (GPT4All)
- ✅ PDF document processing
- ✅ Semantic search with FAISS
- ✅ Response caching (60-70% faster)
- ✅ Multi-user authentication
- ✅ Modern React UI with TailwindCSS

## 🎯 Key Features
- **Offline-first**: Works without internet
- **Fast responses**: 3-5s first query, <0.1s cached
- **Smart search**: Vector similarity with embeddings
- **Secure**: Password hashing, session management

## 📝 Notes
- First run will download AI models (~4GB)
- Models are stored in `backend/models/`
- Database created automatically on first run
- Upload PDFs via Resources page to enable AI search

## 🐛 Troubleshooting
- If packages fail to install, try: `pip install --upgrade pip`
- If models don't load, check `backend/models/` folder exists
- Clear browser cache if frontend doesn't load properly

## 🔧 Production Deployment
See README.md for production deployment instructions.
