# Deployment Notes

Panduan singkat untuk men-deploy aplikasi SEO & GEO Analyzer di server Linux (Ubuntu) dan Windows Server.

## 1. Prasyarat

- Python 3.10+ terinstal
- pip tersedia
- Git tersedia
- Virtual environment disarankan
- Akses ke port 8000 (atau port lain yang Anda pilih)

## 2. Deploy di Ubuntu / Linux Server

### 2.1 Clone repository

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git
cd /var/www
sudo git clone <repo-url> seo-geo-analyzer-sands
cd seo-geo-analyzer-sands
```

### 2.2 Buat virtual environment dan install dependensi

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Konfigurasi environment

```bash
cp .env.example .env
nano .env
```

Isi variabel berikut:

```env
OLLAMA_API_KEY=your_ollama_cloud_api_key_here
OLLAMA_MODEL=qwen3.5:cloud
OLLAMA_BASE_URL=https://ollama.com
REQUEST_TIMEOUT_SECONDS=15
APP_ENV=production
```

### 2.4 Jalankan aplikasi dengan Uvicorn

Untuk produksi, gunakan host 0.0.0.0 supaya dapat diakses dari luar:

```bash
nohup venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

### 2.5 Opsional: gunakan Nginx sebagai reverse proxy

Contoh konfigurasi Nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Aktifkan konfigurasi:

```bash
sudo ln -s /etc/nginx/sites-available/your-config /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2.6 Jalankan otomatis saat reboot

Gunakan systemd:

```bash
sudo nano /etc/systemd/system/seo-geo-analyzer.service
```

Isi:

```ini
[Unit]
Description=SEO GEO Analyzer
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/seo-geo-analyzer-sands
Environment=PATH=/var/www/seo-geo-analyzer-sands/venv/bin
ExecStart=/var/www/seo-geo-analyzer-sands/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable seo-geo-analyzer
sudo systemctl start seo-geo-analyzer
```

---

## 3. Deploy di Windows Server

### 3.1 Install Python

Pastikan Python 3.10+ sudah terinstal dan ditambahkan ke PATH.

### 3.2 Clone repository

```powershell
cd C:\inetpub\wwwroot
git clone <repo-url> seo-geo-analyzer-sands
cd seo-geo-analyzer-sands
```

### 3.3 Buat virtual environment dan install dependensi

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.4 Konfigurasi environment

```powershell
Copy-Item .env.example .env
notepad .env
```

Isi variabel yang sama seperti di Linux.

### 3.5 Jalankan aplikasi

Untuk Windows, gunakan host localhost atau 0.0.0.0 tergantung kebutuhan:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Jika ada masalah `WinError 10013`, gunakan:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3.6 Opsional: jalankan sebagai Windows Service

Gunakan NSSM atau tugas scheduler untuk menjaga service tetap berjalan.

Contoh dengan NSSM:

```powershell
nssm install SeoGeoAnalyzer "C:\path\to\venv\Scripts\python.exe"
```

Argumen:

```powershell
-m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Set working directory ke folder aplikasi.

---

## 4. Tips Keamanan

- Jangan commit file `.env` ke repository
- Gunakan HTTPS di production
- Batasi akses ke port 8000 menggunakan firewall
- Pastikan `OLLAMA_API_KEY` aman dan tidak tersebar
- Jalankan aplikasi di balik reverse proxy jika memungkinkan

## 5. Health Check

Setelah deploy, cek endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Harus mengembalikan JSON seperti:

```json
{"status": "ok"}
```
