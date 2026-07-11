# SEO & GEO Analyzer

Aplikasi web untuk menganalisa kesiapan SEO (Search Engine Optimization) dan GEO (Generative Engine Optimization) sebuah website. Dilengkapi dengan rekomendasi AI dari Ollama Cloud.

## Fitur

- **Cek robots.txt** — termasuk deteksi status akses untuk AI crawler (GPTBot, ClaudeBot, Google-Extended, dll)
- **Cek sitemap.xml** — validasi format, hitung URL, cek freshness
- **Analisa SEO on-page** — title, meta, heading, canonical, viewport, HTTPS, alt text, structured data, dll
- **Analisa GEO** — kesiapan konten untuk dikutip AI answer engine (FAQ schema, heading Q&A, E-E-A-T, dll)
- **Rekomendasi AI** — saran perbaikan dari Ollama Cloud API dalam bahasa Indonesia

## Tech Stack

- **Backend:** FastAPI + Jinja2 (server-side rendering)
- **Frontend:** HTMX (partial reload tanpa JS framework) + CSS murni (Apple-style design)
- **HTTP Client:** httpx (async)
- **Parsing:** BeautifulSoup4 + lxml (HTML), defusedxml (XML), Protego (robots.txt)
- **AI:** Ollama Cloud API

## Setup

### 1. Clone & Install Dependencies

```bash
cd seo-geo-analyzer-sands
pip install -r requirements.txt
```

### 2. Konfigurasi Environment

```bash
cp .env.example .env
```

Edit file `.env` dan isi `OLLAMA_API_KEY` dengan API key Anda dari https://ollama.com/settings/keys

```env
OLLAMA_API_KEY=your_actual_api_key_here
OLLAMA_MODEL=qwen3.5:cloud
OLLAMA_BASE_URL=https://ollama.com
REQUEST_TIMEOUT_SECONDS=15
APP_ENV=development
```

> **Catatan:** Model harus menggunakan suffix `:cloud`. Cek model cloud yang tersedia di https://ollama.com/search?c=cloud

### 3. Jalankan Aplikasi

Jika Anda menggunakan Windows dan melihat error socket seperti `WinError 10013`, jalankan server dengan host localhost dan port eksplisit:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Buka browser di http://127.0.0.1:8000/

## API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/` | Halaman form input URL |
| POST | `/analyze` | Analisa URL (returns partial HTML untuk HTMX) |
| GET | `/health` | Health check |

## Struktur Folder

```
seo-geo-analyzer-sands/
├── app/
│   ├── main.py                  # Entry point FastAPI
│   ├── config.py                # Environment variables
│   ├── models.py                # Pydantic models
│   ├── services/
│   │   ├── fetcher.py           # Async HTTP fetcher
│   │   ├── robots_checker.py    # Analisa robots.txt
│   │   ├── sitemap_checker.py   # Analisa sitemap.xml
│   │   ├── seo_analyzer.py      # Analisa SEO on-page
│   │   ├── geo_analyzer.py      # Analisa GEO
│   │   └── ai_advisor.py        # Ollama Cloud API
│   ├── routes/
│   │   └── analyze.py           # POST /analyze endpoint
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── partials/
│   │       └── result.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── .env.example
├── requirements.txt
└── README.md
```
