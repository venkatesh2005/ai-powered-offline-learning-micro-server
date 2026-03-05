# Raspberry Pi 5 Deployment Checklist
## AI-Powered Offline Learning Micro-Server

Target hardware: **Raspberry Pi 5 (8 GB RAM)**  
OS: **Raspberry Pi OS Bookworm (64-bit, headless)**  
Model: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (669 MB, already in `backend/models/`)

---

## 1. OS Installation & First Boot

```bash
# Flash Raspberry Pi OS Bookworm 64-bit (Lite recommended — no desktop)
# Use Raspberry Pi Imager → pick "Raspberry Pi OS Lite (64-bit)"
# In Imager advanced settings:
#   ✅ Set hostname:   learning-pi
#   ✅ Enable SSH
#   ✅ Set username:   pi   (or your preferred name)
#   ✅ Set password
#   ✅ Configure Wi-Fi (or use Ethernet)

# First SSH into the Pi
ssh pi@learning-pi.local

# Full system update first
sudo apt update && sudo apt full-upgrade -y
sudo apt autoremove -y
```

---

## 2. OS Tweaks for Performance

### 2a. Disable unused services to free RAM
```bash
# Disable Bluetooth (not needed for a server)
sudo systemctl disable bluetooth hciuart --now

# Disable Wi-Fi power saving (prevents connection drops)
sudo iw dev wlan0 set power_save off
# Make it permanent
echo "wireless-power off" | sudo tee -a /etc/NetworkManager/conf.d/default-wifi-powersave-on.conf

# Optionally disable Wi-Fi entirely if using Ethernet
# sudo rfkill block wifi

# Disable unnecessary services
sudo systemctl disable avahi-daemon --now   # mDNS (optional — keep if using .local hostname)
sudo systemctl disable man-db.timer --now  # Man page indexing
```

### 2b. GPU memory split — give all RAM to CPU
```bash
# Allocate minimum GPU memory (server has no display)
echo "gpu_mem=16" | sudo tee -a /boot/firmware/config.txt
```

### 2c. Enable PCIe Gen 3 for NVMe (optional, Pi 5 only)
```bash
# Only if you have an NVMe SSD via M.2 HAT
echo "dtparam=pciex1_gen=3" | sudo tee -a /boot/firmware/config.txt
```

### 2d. Set USB power limits (prevents throttling on USB-C power adapters)
```bash
# Ensure Pi 5 gets max current from USB-C adapter
echo "usb_max_current_enable=1" | sudo tee -a /boot/firmware/config.txt
```

---

## 3. Swap Memory Configuration

> The sentence-transformers model and llama-cpp-python together use ~2–3 GB RAM.
> With 8 GB this is fine, but swap provides a safety net.

```bash
# Disable the default tiny swap
sudo dphys-swapfile swapoff
sudo systemctl disable dphys-swapfile

# Install zram-tools (compressed swap in RAM — much faster than SD card swap)
sudo apt install zram-tools -y

# Configure zram: 2 GB compressed swap
sudo tee /etc/default/zramswap > /dev/null <<EOF
ALGO=lz4
PERCENT=25
EOF

sudo systemctl enable zramswap --now

# Tune swappiness (10 = only use swap when truly needed)
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.d/99-sysctl.conf
echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.d/99-sysctl.conf
sudo sysctl --system

# Verify
zramctl
free -h
```

---

## 4. CPU Governor — Performance Mode

> Raspberry Pi 5 defaults to `ondemand`. Switch to `performance` to avoid
> frequency ramp-up delays during LLM token generation.

```bash
# Install cpufrequtils
sudo apt install cpufrequtils -y

# Set to performance governor
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils

# Apply immediately to all 4 cores
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee "$cpu"
done

# Verify — all 4 cores should show "performance"
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Confirm current clock speed (should be ~2400 MHz on Pi 5)
vcgencmd measure_clock arm
```

> **Optional overclock** (Pi 5 is thermally safe at 2.8 GHz with active cooling):
> ```
> # /boot/firmware/config.txt
> arm_freq=2800
> over_voltage_delta=50000
> ```

---

## 5. Install Python & Build Tools

```bash
# Python 3.11 ships with Bookworm — no need to install
python3 --version   # Should show 3.11.x

# Install system dependencies needed by the pip packages
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    ninja-build \
    git \
    libopenblas-dev \      # FAISS / numpy acceleration
    libatlas-base-dev \    # NumPy BLAS backend
    libhdf5-dev \          # transformers optional
    libjpeg-dev \
    libpng-dev \
    pkg-config
```

---

## 6. Transfer Project Files

```bash
# Option A — rsync from your dev machine
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude 'node_modules' \
    "AI-Powered Offline Learning Micro-Server/" \
    pi@learning-pi.local:~/learning-server/

# Option B — Git clone (if repo is hosted privately)
# git clone https://your-repo.git ~/learning-server

# Option C — USB stick
# Copy the entire project folder to a USB drive and mount it on the Pi
```

---

## 7. Python Virtual Environment

```bash
cd ~/learning-server

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip first
pip install --upgrade pip wheel setuptools
```

---

## 8. Required pip Packages

Install in this order to avoid build conflicts:

### Step 1 — Core numeric libs first (ensures correct BLAS linkage)
```bash
pip install numpy==2.1.3
```

### Step 2 — llama-cpp-python (prebuilt CPU wheel — avoids long compilation)
```bash
# Option A: pre-built wheel (fastest, recommended)
pip install llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# Option B: compile from source (if pre-built wheel unavailable for your Python version)
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
    pip install llama-cpp-python
```

### Step 3 — All remaining packages
```bash
pip install \
    Flask==3.0.0 \
    Flask-SQLAlchemy==3.1.1 \
    Flask-CORS==4.0.0 \
    Flask-Compress==1.14 \
    sentence-transformers==3.3.1 \
    faiss-cpu==1.9.0.post1 \
    transformers==4.46.3 \
    pdfplumber==0.11.4 \
    cachetools==5.5.0 \
    diskcache==5.6.3 \
    python-dotenv==1.0.0 \
    psutil==7.1.0 \
    "Werkzeug==3.0.1" \
    gunicorn \
    zram-tools   # skip — this is an apt package, not pip
```

Or install from the requirements file:
```bash
pip install -r backend/requirements.txt
pip install gunicorn   # production WSGI server — not in requirements.txt
```

### Verify all imports load correctly
```bash
python3 - <<'EOF'
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer
import faiss, flask, pdfplumber, cachetools
print("✅ All imports OK")
EOF
```

---

## 9. Environment Configuration

```bash
# Create .env in backend/
cat > ~/learning-server/backend/.env <<'EOF'
FLASK_ENV=production
SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_THIS_PASSWORD
GPT4ALL_MODEL=tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
MODELS_PATH=models
RESOURCES_PATH=resources
# Replace with Pi's actual LAN IP — find with: hostname -I
CORS_ORIGINS=http://192.168.1.100:5000,http://192.168.1.100:3000
EOF

# Secure the .env file
chmod 600 ~/learning-server/backend/.env
```

> Find your Pi's IP: `hostname -I | awk '{print $1}'`

---

## 10. Frontend Production Build

The React frontend must be built into static files so Flask can serve it
directly — **no Node.js required at runtime on the Pi**.

### Build on your dev machine (recommended — Pi has limited RAM for builds)
```bash
# On your development machine:
cd frontend
npm install
npm run build
# This creates frontend/dist/ with static HTML/CSS/JS

# Transfer the built dist/ to the Pi
rsync -avz frontend/dist/ pi@learning-pi.local:~/learning-server/frontend/dist/
```

### Or build directly on the Pi (needs Node.js installed)
```bash
# Install Node.js 20 LTS on Pi
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

cd ~/learning-server/frontend
npm install
npm run build

# Remove node_modules after build to free SD card space
rm -rf node_modules
```

Flask is already configured to serve `static/dist` — copy build output there:
```bash
cp -r ~/learning-server/frontend/dist/* ~/learning-server/backend/static/dist/
```

---

## 11. Directory Setup

```bash
cd ~/learning-server/backend
mkdir -p instance embeddings_cache resources/uploads resources/sample logs models
chmod 755 instance embeddings_cache resources/uploads
```

---

## 12. Production Server with Gunicorn

```bash
# Test manually first
cd ~/learning-server/backend
source ../.venv/bin/activate
gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 300 \
    --worker-class gthread app:app

# workers=1  — only 1 process; the AI model is loaded once (not duplicated per worker)
# threads=4  — handles concurrent requests within the single worker
# timeout=300 — 5 min timeout; LLM can be slow on first request
```

### Create systemd service for auto-start
```bash
sudo tee /etc/systemd/system/learning-server.service > /dev/null <<'EOF'
[Unit]
Description=AI-Powered Offline Learning Server
After=network.target
Wants=network.target

[Service]
Type=exec
User=pi
WorkingDirectory=/home/pi/learning-server/backend
EnvironmentFile=/home/pi/learning-server/backend/.env
ExecStart=/home/pi/learning-server/.venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --worker-class gthread \
    --log-level info \
    --access-logfile /home/pi/learning-server/backend/logs/access.log \
    --error-logfile /home/pi/learning-server/backend/logs/error.log \
    app:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable learning-server
sudo systemctl start learning-server

# Check status
sudo systemctl status learning-server
sudo journalctl -u learning-server -f   # live logs
```

---

## 13. Static IP (Recommended)

Assign the Pi a fixed LAN IP so mobile devices always connect to the same address.

### Via dhcpcd (Raspberry Pi OS default)
```bash
sudo tee -a /etc/dhcpcd.conf > /dev/null <<'EOF'

interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
EOF

sudo systemctl restart dhcpcd
```

> Or assign a DHCP reservation via your router's admin panel using the Pi's MAC address.

---

## 14. Firewall

```bash
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh        # port 22
sudo ufw allow 5000/tcp   # Flask / Gunicorn API
sudo ufw allow 3000/tcp   # Only if also serving Vite dev server (not for prod)
sudo ufw enable

sudo ufw status
```

---

## 15. Thermal Management

> TinyLlama inference on Pi 5 will push CPU to ~80% for 10–30 seconds per query.
> Active cooling is essential.

```bash
# Check current temperature
vcgencmd measure_temp

# Watch temperature live during an LLM query
watch -n 1 vcgencmd measure_temp

# Throttle check — should show all zeros if cooling is adequate
vcgencmd get_throttled
# 0x0 = no throttling — good
# 0x50005 = thermal throttling occurred — add heatsink / fan
```

**Recommended cooling for sustained AI inference:**
- Official Raspberry Pi 5 Active Cooler (fan + heatsink)  
- Or Argon NEO 5 BRED case with integrated fan

---

## 16. First-Run Verification

```bash
# After systemd service starts, check AI preload logs
sudo journalctl -u learning-server --since "5 minutes ago"

# Expected output (within ~2 min of boot):
#   📥 [Embeddings] Loading SentenceTransformer: all-MiniLM-L6-v2...
#   ✅ [Embeddings] Model loaded in Xs
#   🤖 [ChatBot] Loading llama-cpp-python model...
#   ✅ [ChatBot] Model loaded in 1-3s
#   ✅ [Startup] AI preload complete in Xs — server is READY

# Hit the status endpoint
curl http://localhost:5000/api/status | python3 -m json.tool

# Expected:
# {
#   "server": "online",
#   "startup_complete": true,
#   "embeddings_loaded": true,
#   "faiss_index_loaded": true,
#   "chatbot_loaded": true,
#   "documents_indexed": N
# }
```

---

## 17. Performance Expectations on Pi 5

| Operation | Expected Time |
|---|---|
| Server cold start → models ready | ~90–120 s (sentence-transformers downloads on first boot) |
| Subsequent restarts (models cached) | ~5–15 s |
| FAISS search (5 results) | < 20 ms |
| LLM first token (theory, 100 tokens) | 8–15 s |
| LLM first token (code, 150 tokens) | 12–25 s |
| Cached response (TTL hit) | < 1 ms |

> sentence-transformers downloads `all-MiniLM-L6-v2` (~90 MB) on first run.
> Subsequent runs use the `~/.cache/huggingface/` cache — no internet needed.

---

## 18. Quick Deployment Checklist Summary

```
[ ] Flash Raspberry Pi OS Bookworm 64-bit Lite
[ ] sudo apt update && sudo apt full-upgrade -y
[ ] gpu_mem=16  added to /boot/firmware/config.txt
[ ] zramswap configured and enabled
[ ] vm.swappiness=10 set in sysctl
[ ] CPU governor set to performance
[ ] System build deps installed (cmake, ninja, libopenblas-dev, etc.)
[ ] Project files transferred to ~/learning-server/
[ ] Python venv created and activated
[ ] numpy installed first
[ ] llama-cpp-python installed (pre-built wheel)
[ ] All remaining pip packages installed
[ ] backend/.env configured with production SECRET_KEY and password
[ ] Frontend built (npm run build) and dist/ copied to backend/static/dist/
[ ] instance/, embeddings_cache/, resources/uploads/, logs/ directories created
[ ] Static IP assigned (via dhcpcd or router DHCP reservation)
[ ] UFW firewall configured (allow 22, 5000)
[ ] gunicorn tested manually (workers=1, threads=4, timeout=300)
[ ] systemd service created, enabled, and started
[ ] /api/status returns startup_complete: true
[ ] Temperature stays below 80°C under load (vcgencmd measure_temp)
[ ] Login with admin credentials works from a phone on the same Wi-Fi
[ ] PDF upload and AI chat tested end-to-end
```
