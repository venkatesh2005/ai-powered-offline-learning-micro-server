# AI Models Directory

## 📥 Download Required Model

**The AI models are NOT included in this repository due to their large file size.**

### TinyLlama 1.1B (Recommended - Fastest)

**Direct Download Link:**
```
https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

**Download Instructions:**

**Method 1: Browser Download**
1. Click the link above or paste it in your browser
2. Save the file as: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
3. Move it to this directory: `backend/models/`

**Method 2: Command Line (Windows)**
```powershell
cd backend/models
curl -L -o tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

**Method 3: Command Line (Linux/Mac)**
```bash
cd backend/models
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

**File Details:**
- Size: ~650 MB
- Format: GGUF (GPT4All compatible)
- Quantization: Q4_K_M (4-bit, medium quality)
- Performance: 2-5 seconds per response on CPU

---

## 🔄 Alternative Models (Optional)

### Orca Mini 3B (Better Quality, Slower)

**Download:** https://huggingface.co/pankajmathur/orca_mini_3b/resolve/main/ggml-model-q4_0.gguf

**Instructions:**
1. Download the file
2. Rename to: `orca-mini-3b-gguf2-q4_0.gguf`
3. Place in this directory
4. Update `backend/.env`: `GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf`

**Performance:** 5-10 seconds per response on CPU

---

## ✅ Verification

After downloading, your directory should look like:
```
backend/models/
├── .gitkeep
├── README.md (this file)
└── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf (650MB)
```

Verify the model is in place:
```bash
# Windows PowerShell
dir backend\models\*.gguf

# Linux/Mac
ls -lh backend/models/*.gguf
```

---

## ⚠️ Important Notes

1. **At least ONE model file is required** for the application to work
2. Models are excluded from Git due to large file size
3. TinyLlama is recommended for fastest response times
4. All models run completely offline (no internet needed after download)
5. Model files should have `.gguf` extension

---

## 🆘 Troubleshooting

**Problem:** Download is very slow
- Try using a download manager
- Consider downloading during off-peak hours
- HuggingFace servers may be temporarily slow

**Problem:** File is corrupted
- Re-download the file
- Verify file size matches (~650MB for TinyLlama)
- Check your disk has enough space

**Problem:** Model not loading
- Ensure filename matches exactly: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
- Check file is in correct directory: `backend/models/`
- Verify `.env` has correct `GPT4ALL_MODEL` setting

---

## 📊 Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| TinyLlama 1.1B | 650MB | ⚡⚡⚡ Fast | ⭐⭐ Good | Quick responses, limited hardware |
| Orca Mini 3B | 1.9GB | ⚡⚡ Medium | ⭐⭐⭐ Better | Better quality answers, more RAM |

---

**Need help?** Check the main `GITHUB_SETUP_GUIDE.md` or `README.md` for more information.
