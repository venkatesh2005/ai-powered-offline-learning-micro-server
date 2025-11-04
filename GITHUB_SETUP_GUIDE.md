# 🚀 AI-Powered Offline Learning Micro Server - GitHub Setup & Installation Guide

## 📋 Project Overview
AI-Powered Offline Learning Micro Server is an intelligent learning platform with offline chatbot capabilities, resource management, and quiz functionality using a lightweight micro server architecture.

---

## 🎯 Quick Start (For Users Cloning from GitHub)

### Prerequisites
- **Python 3.8+** installed
- **Node.js 16+** and npm installed
- **Git** installed
- At least **4GB RAM** available
- **2GB disk space** for dependencies and model

### Step 1: Clone the Repository
```bash
git clone https://github.com/venkatesh2005/ai-powered-offline-learning-micro-server.git
cd ai-powered-offline-learning-micro-server
```

### Step 2: Backend Setup

#### 2.1 Navigate to Backend
```bash
cd backend
```

#### 2.2 Create Virtual Environment
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.3 Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 2.4 Create Environment File
Create a `.env` file in the `backend` folder:
```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this-in-production
FLASK_ENV=development

# Admin Credentials (CHANGE THESE!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# AI Models (TinyLlama is included, fastest option)
GPT4ALL_MODEL=tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# Paths
RESOURCES_PATH=resources
MODELS_PATH=models
```

#### 2.5 Initialize Database
```bash
python -m database.init_db
```

#### 2.6 Download AI Model (Required)
**The AI model is NOT included in the repository due to its large size (650MB).**

**Download TinyLlama Model:**
1. **Download link:** https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
2. Save the file to: `backend/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
3. File size: ~650MB
4. This is the fastest model for CPU-only systems

**Alternative Models (Optional):**
- **Orca Mini (3B)** - Better quality, slower (2-3x slower than TinyLlama)
  - Download: https://huggingface.co/pankajmathur/orca_mini_3b/resolve/main/ggml-model-q4_0.gguf
  - Rename to: `orca-mini-3b-gguf2-q4_0.gguf`
  - Place in: `backend/models/`
  - Update `.env`: `GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf`

**⚠️ Important:** The application won't work without downloading at least one model!

#### 2.7 Initialize Database
```bash
python app.py
```
Backend will run at: `http://127.0.0.1:5000`

### Step 3: Frontend Setup

#### 3.1 Open New Terminal and Navigate to Frontend
```bash
cd frontend
```

#### 3.2 Install Node Dependencies
```bash
npm install
```

#### 3.3 Start Development Server
```bash
npm run dev
```
Frontend will run at: `http://localhost:5173`

### Step 4: Access the Application
1. Open browser: `http://localhost:5173`
2. Login with:
   - **Username:** `admin`
   - **Password:** `admin123` (change this!)

---

## 📁 Project Structure

```
ai-powered-offline-learning-micro-server/
├── backend/                    # Flask Backend
│   ├── ai/                    # AI modules
│   │   ├── chatbot.py        # GPT4All chatbot
│   │   ├── embeddings.py     # Vector embeddings
│   │   └── pdf_processor.py  # Document processing
│   ├── database/              # Database models
│   ├── models/                # AI model files (GGUF format)
│   │   └── .gitkeep          # Download TinyLlama here (see setup guide)
│   ├── resources/             # Uploaded files
│   ├── app.py                # Main Flask app
│   ├── config.py             # Configuration
│   └── requirements.txt      # Python dependencies
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   └── api/             # API configuration
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite configuration
│
└── GITHUB_SETUP_GUIDE.md     # This file!
```

---

## 🔧 Configuration Options

### Switching AI Models
Edit `backend/.env`:
```env
# For fastest responses (included):
GPT4ALL_MODEL=tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

# For better quality (download separately):
GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf
```

### Network Access (LAN/Mobile)
To access from other devices on your network:

1. Find your local IP:
   - **Windows:** `ipconfig` (look for IPv4)
   - **Linux/Mac:** `ifconfig` or `ip addr`

2. Update `backend/config.py` CORS_ORIGINS to include your IP:
   ```python
   default_origins = 'http://localhost:3000,http://YOUR_IP:5173'
   ```

3. Access from other devices: `http://YOUR_IP:5173`

---

## 🎮 Features

- ✅ **Offline AI Chatbot** - Works without internet using local models
- ✅ **RAG (Retrieval Augmented Generation)** - Answer questions from uploaded documents
- ✅ **Resource Management** - Upload PDFs, presentations, videos
- ✅ **Quiz System** - Create and take quizzes
- ✅ **Admin Panel** - Manage content and users
- ✅ **Fast Responses** - Optimized with caching (2-5 seconds per response)

---

## 🐛 Troubleshooting

### Backend Issues

**Problem:** `ModuleNotFoundError`
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt
```

**Problem:** `Model file not found`
```bash
# Solution: Download the TinyLlama model
# Visit: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
# Save to: backend/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
# Verify the file is in the correct location
ls backend/models/
```

**Problem:** Database errors
```bash
# Solution: Reinitialize database
cd backend
python -m database.init_db
```

### Frontend Issues

**Problem:** `Cannot connect to backend`
- Check if backend is running on port 5000
- Verify `frontend/src/api/axios.js` has correct API URL

**Problem:** `npm install` fails
```bash
# Solution: Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Performance Issues

**Problem:** Slow responses (>10 seconds)
- Ensure you're using TinyLlama model (fastest)
- Check CPU usage during inference
- Consider upgrading to Orca only if you need better quality

---

## 🔒 Security Notes

**Before deploying to production:**
1. Change `SECRET_KEY` in `.env`
2. Change `ADMIN_PASSWORD` in `.env`
3. Use HTTPS for production
4. Update CORS origins to your production domain
5. Set `FLASK_ENV=production` in `.env`

---

## 📦 What's Included in the Repository

✅ Complete backend code  
✅ Complete frontend code  
✅ Configuration templates  
✅ Setup documentation  
✅ Sample resources  

❌ Not included (download/install separately):  
- AI Models (TinyLlama ~650MB) - **Download link provided in setup steps**
- `node_modules/` - Install with `npm install`
- `venv/` - Create with `python -m venv venv`
- Database files - Created with `init_db.py`
- Embeddings cache - Generated on first use

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

---

## 📄 License

See LICENSE file for details.

---

## 🆘 Need Help?

- Check existing documentation: `README.md`, `SETUP.md`
- Review optimization guides: `SPEED_OPTIMIZATION.md`
- Check troubleshooting section above
- Review debug logs in `backend/` folder

---

## ⚡ Performance Tips

1. **Use TinyLlama** for fastest responses (2-5 seconds)
2. **Upload relevant documents** for better RAG responses
3. **Close other applications** to free up RAM during AI inference
4. **Use SSD storage** for faster model loading
5. **Cache is automatic** - repeated questions are answered instantly

---

**Happy Coding! 🎓💻**
