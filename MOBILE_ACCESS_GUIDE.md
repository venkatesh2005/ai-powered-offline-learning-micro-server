# 📱 Mobile Access Setup Guide

## ✅ Changes Made

Your application is now configured to work on mobile devices on the same network!

### What Was Changed:

1. **Frontend (axios.js)**: Updated to use your computer's IP address (10.50.173.74) instead of localhost
2. **Backend (config.py)**: Added your computer's IP to CORS allowed origins
3. **Backend (app.py)**: Changed server to listen on `0.0.0.0` (all network interfaces) instead of just localhost

---

## 🚀 How to Use

### Step 1: Start the Backend Server

Open a terminal in the `backend` folder and run:

```powershell
cd backend
python app.py
```

**Important**: The server will now show:
```
API Server: http://0.0.0.0:5000
```
This means it's accepting connections from the network!

### Step 2: Start the Frontend Server

Open another terminal in the `frontend` folder and run:

```powershell
cd frontend
npm run dev
```

The frontend will start on port 5173 (Vite default).

### Step 3: Access from Your Phone

On your phone's browser (make sure you're on the **same WiFi network**), navigate to:

```
http://10.50.173.74:5173
```

**That's it!** 🎉 Your application should now work fully on your phone, including login, API calls, and all features.

---

## 🔧 Troubleshooting

### Issue: "Network Failed" or "Cannot connect"

**Solution 1: Check Firewall**
Windows Firewall might be blocking the connections. You need to allow Python through the firewall:

1. Open **Windows Defender Firewall**
2. Click **"Allow an app through firewall"**
3. Find **Python** in the list (or add it)
4. Make sure **both Private and Public** are checked
5. Click **OK**

**Solution 2: Verify IP Address**
Your computer's IP address might have changed. Run this to check:

```powershell
ipconfig | Select-String -Pattern "IPv4"
```

If it's different from `10.50.173.74`, you'll need to update:
- `frontend/src/api/axios.js` - change the IP address
- `backend/config.py` - update the CORS_ORIGINS with the new IP

### Issue: Frontend doesn't load on phone

**Check**: Make sure you're accessing the correct port:
- Frontend (Vite): `http://10.50.173.74:5173`
- Backend API: `http://10.50.173.74:5000`

### Issue: CORS errors in browser console

**Solution**: Make sure `backend/config.py` includes your computer's IP in CORS_ORIGINS.

---

## 🔒 Security Notes

### ⚠️ Important for Production:

1. **Change Default Passwords**: Update admin password in backend
2. **Use HTTPS**: For production, use HTTPS instead of HTTP
3. **Restrict CORS**: Only allow specific domains in CORS_ORIGINS
4. **Firewall Rules**: Only open required ports

### For Development (Current Setup):

- This setup is **safe for local network** testing
- Don't expose this setup to the public internet without proper security
- Keep your WiFi network password protected

---

## 📝 Configuration Files Changed

### 1. `frontend/src/api/axios.js`
```javascript
const apiURL = import.meta.env.VITE_API_URL || 'http://10.50.173.74:5000'
axios.defaults.baseURL = apiURL
```

### 2. `backend/config.py`
```python
default_origins = 'http://localhost:3000,...,http://10.50.173.74:5173'
CORS_ORIGINS = os.getenv('CORS_ORIGINS', default_origins).split(',')
```

### 3. `backend/app.py`
```python
app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
```

---

## 🌐 Accessing from Different Devices

### From Your Computer:
- `http://localhost:5173` ✅
- `http://127.0.0.1:5173` ✅
- `http://10.50.173.74:5173` ✅

### From Your Phone (Same WiFi):
- `http://10.50.173.74:5173` ✅

### From Another Computer (Same WiFi):
- `http://10.50.173.74:5173` ✅

---

## 💡 Tips

1. **Bookmark on Phone**: Save `http://10.50.173.74:5173` to your phone's home screen for quick access
2. **Check WiFi**: Ensure both devices are on the **same WiFi network**
3. **IP Changes**: Your IP might change if you reconnect to WiFi. Check it with `ipconfig` if it stops working
4. **Performance**: Mobile access works great! The AI chatbot will work just as fast as on your computer

---

## 🎯 Next Steps

Want to make this permanent? Consider:

1. **Set Static IP**: Configure your computer to always use the same local IP
2. **Environment Variables**: Use `.env` file for easy IP configuration:
   ```
   VITE_API_URL=http://10.50.173.74:5000
   ```
3. **Build for Production**: Create a production build that can be deployed to a server

---

## ❓ Need Help?

If you encounter any issues:

1. Check that both backend and frontend servers are running
2. Verify you're on the same WiFi network
3. Check Windows Firewall settings
4. Confirm the IP address hasn't changed with `ipconfig`

Enjoy using your AI Learning Hub on mobile! 🎉📱
