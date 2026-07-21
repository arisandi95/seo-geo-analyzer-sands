```
_____ ______ ____              _____ ______ ____  
 / ____|  ____/ __ \    ___     / ____|  ____/ __ \ 
| (___ | |__ | |  | |  ( _ )   | |  __| |__ | |  | |
 \___ \|  __|| |  | |  / _ \/\ | | |_ |  __|| |  | |
 ____) | |___| |__| | | (_>  < | |__| | |___| |__| |
|_____/|______\____/   \___/\/  \_____|______\____/
                                             
```

# SEO & GEO Analyzer v2.0.0

Aplikasi web untuk menganalisa kesiapan SEO (Search Engine Optimization) dan GEO (Generative Engine Optimization) sebuah website. Dilengkapi riwayat analisis, fitur perbandingan URL, ekspor PDF, dan rekomendasi AI dari Ollama Cloud.

## Fitur

- **Cek robots.txt** — termasuk deteksi status akses untuk 7 AI crawler (GPTBot, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, CCBot, Bytespider)
- **Cek sitemap.xml** — validasi format, hitung URL, cek freshness (lastmod), dukung sitemap index & urlset
- **Analisa SEO on-page** — title, meta description, heading structure, canonical, viewport, HTTPS, alt text, Open Graph, Twitter Cards, JSON-LD structured data, word count, internal/external links
- **Analisa GEO** — kesiapan konten untuk dikutip AI answer engine: FAQ/QAPage schema, question-based heading, E-E-A-T (Person/Organization schema), freshness signal, llms.txt
- **Rekomendasi AI** — saran perbaikan dari Ollama Cloud API dalam bahasa Indonesia (streaming, markdown)
- **Riwayat & Permalink** — setiap hasil analisis otomatis tersimpan, bisa diakses via tautan permanen `/r/{id}`
- **Perbandingan URL** — bandingkan dua website secara side-by-side dengan pemenang tiap kategori + analisis AI kompetitif
- **Ekspor PDF** — unduh laporan analisis sebagai PDF (WeasyPrint, fallback print CSS)
- **Multi-page Audit** — audit mini hingga 10 URL dari sitemap secara paralel, agregasi isu umum
- **Cek Tambahan** — redirect consistency (www/non-www, http/https), favicon, hreflang, soft-404, page size, response time
- **Generator** — rekomendasi robots.txt, FAQPage JSON-LD, dan llms.txt siap pakai
- **Trend Chart** — grafik perkembangan skor SEO & GEO per domain (SVG server-side)
- **Rate Limiting** — proteksi abuse: 10x/menit untuk analyze, 3x/menit untuk multi-page
- **SSRF Guard** — proteksi Server-Side Request Forgery (blokir IP private/loopback)
- **Caching** — cache robots.txt & llms.txt per domain (TTL 10 menit, max 100 entri)

## Tech Stack

- **Backend:** FastAPI + Jinja2 (server-side rendering) + SQLAlchemy async + aiosqlite
- **Frontend:** HTMX (partial reload tanpa JS framework) + CSS murni (Apple-style design)
- **HTTP Client:** httpx (async, connection pooling)
- **Parsing:** BeautifulSoup4 + lxml (HTML), defusedxml (XML safe), Protego (robots.txt)
- **AI:** Ollama Cloud API (streaming chat, competitive analysis)
- **Database:** SQLite via aiosqlite + SQLAlchemy 2.0 async
- **Utilitas:** slowapi (rate limit), cachetools (TTL cache), bleach (HTML sanitasi), WeasyPrint (PDF)

## Setup

### 1. Clone & Install Dependencies

```bash
cd seo-geo-analyzer-sands
pip install -r requirements.txt
```

> **Catatan:** `weasyprint` membutuhkan GTK pada Windows — jika gagal, ekspor PDF akan fallback ke print CSS.

### 2. Konfigurasi Environment

```bash
cp .env.example .env
```

Edit file `.env` dan sesuaikan konfigurasi:

```env
# === API AI ===
OLLAMA_API_KEY=your_ollama_cloud_api_key_here
OLLAMA_MODEL=qwen3.5:cloud
OLLAMA_BASE_URL=https://ollama.com

# === App ===
APP_ENV=development
REQUEST_TIMEOUT_SECONDS=15

# === Database ===
DATABASE_URL=sqlite+aiosqlite:///./data/analyzer.db

# === Multi-page ===
MAX_MULTI_PAGE_URLS=10
MULTI_PAGE_CONCURRENCY=3

# === Rate Limit ===
RATE_LIMIT_ANALYZE=10/minute

# === AI ===
AI_STREAM_TIMEOUT_SECONDS=90
```

> **Catatan:** Model Ollama harus menggunakan suffix `:cloud`. Cek model cloud yang tersedia di https://ollama.com/search?c=cloud

### 3. Jalankan Aplikasi

Jika Anda menggunakan Windows dan melihat error socket seperti `WinError 10013`, jalankan server dengan host localhost dan port eksplisit:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Buka browser di http://127.0.0.1:8000/

## API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/` | Halaman utama (form input URL) |
| POST | `/analyze` | Analisa URL (returns partial HTML untuk HTMX) |
| GET | `/health` | Health check (`{"status":"ok","env":"..."}`) |
| GET | `/history` | Riwayat analisis (paginasi, 20/halaman) |
| GET | `/history/trend` | Grafik tren skor per domain (SVG) |
| GET | `/r/{id}` | Tautan permanen hasil analisis |
| GET | `/r/{id}/pdf` | Ekspor laporan PDF |
| GET | `/compare` | Form perbandingan 2 URL |
| POST | `/compare` | Bandingkan 2 URL (side-by-side) |

## Struktur Folder

```
seo-geo-analyzer-sands/
├── app/
│   ├── main.py                  # Entry point FastAPI (v2.0.0)
│   ├── config.py                # Environment variables via python-dotenv
│   ├── models.py                # Pydantic request/response models
│   ├── models_db.py             # SQLAlchemy ORM (AnalysisRecord)
│   ├── db.py                    # SQLite async engine + session
│   ├── services/
│   │   ├── fetcher.py           # Async HTTP fetcher with SSRF guard & TTL cache
│   │   ├── robots_checker.py    # Analisa robots.txt (Protego + 7 AI crawler)
│   │   ├── sitemap_checker.py   # Analisa sitemap.xml (defusedxml)
│   │   ├── seo_analyzer.py      # Analisa SEO on-page (387+ baris)
│   │   ├── geo_analyzer.py      # Analisa GEO readiness
│   │   ├── ai_advisor.py        # Ollama Cloud API (streaming chat)
│   │   ├── history_service.py   # CRUD riwayat analisis ke SQLite
│   │   ├── multi_page.py        # Audit mini multi-URL via sitemap
│   │   ├── extra_checks.py      # Redirect, favicon, hreflang, dll
│   │   ├── generators.py        # Generator robots.txt, FAQPage, llms.txt
│   │   └── markdown_render.py   # Markdown → HTML aman (bleach)
│   ├── routes/
│   │   ├── analyze.py           # POST /analyze
│   │   ├── history.py           # GET /history, /r/{id}, /history/trend
│   │   ├── export.py            # GET /r/{id}/pdf
│   │   └── compare.py           # GET/POST /compare
│   ├── templates/
│   │   ├── base.html            # Layout utama (navbar Apple-style)
│   │   ├── index.html           # Halaman utama
│   │   ├── history.html         # Riwayat + paginasi
│   │   ├── permalink.html       # Hasil tersimpan
│   │   ├── compare.html         # Form bandingkan
│   │   ├── 404.html             # Halaman error
│   │   ├── report_pdf.html      # Template PDF
│   │   ├── report_print.html    # Template cetak
│   │   └── partials/
│   │       ├── result.html      # Hasil analisis (HTMX partial)
│   │       └── compare_result.html  # Hasil perbandingan (HTMX partial)
│   └── static/
│       ├── css/style.css        # Design system Apple-style
│       └── js/app.js            # Client-side JS
├── .env.example
├── requirements.txt
├── DEPLOY_PLAN.md
├── DEPLOY_NOTES.md
└── README.md
```
