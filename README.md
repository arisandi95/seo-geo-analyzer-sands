_____ ______ ____              _____ ______ ____  
 / ____|  ____/ __ \    ___     / ____|  ____/ __ \ 
| (___ | |__ | |  | |  ( _ )   | |  __| |__ | |  | |
 \___ \|  __|| |  | |  / _ \/\ | | |_ |  __|| |  | |
 ____) | |___| |__| | | (_>  < | |__| | |___| |__| |
|_____/|______\____/   \___/\/  \_____|______\____/
                                             
```

# SEO & GEO Analyzer v2.1.0

Aplikasi web untuk menganalisa kesiapan SEO (Search Engine Optimization) dan GEO (Generative Engine Optimization) sebuah website. Dilengkapi riwayat analisis, fitur perbandingan URL, ekspor PDF, rekomendasi AI dari Ollama Cloud, analisis teknologi website, PageSpeed Insights & Core Web Vitals, serta estimasi kata kunci dan backlink berbasis AI.

## Fitur

### Analisis Dasar
- **Cek robots.txt** — termasuk deteksi status akses untuk 7 AI crawler (GPTBot, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, CCBot, Bytespider)
- **Cek sitemap.xml** — validasi format, hitung URL, cek freshness (lastmod), dukung sitemap index & urlset
- **Analisa SEO on-page** — title, meta description, heading structure, canonical, viewport, HTTPS, alt text, Open Graph, Twitter Cards, JSON-LD structured data, word count, internal/external links
- **Analisa GEO** — kesiapan konten untuk dikutip AI answer engine: FAQ/QAPage schema, question-based heading, E-E-A-T (Person/Organization schema), freshness signal, llms.txt
- **Technology Results** — deteksi teknologi website dari HTML + response headers: CMS (WordPress, Joomla, Drupal, dll), JavaScript framework (React, Next.js, Vue, Angular, Alpine.js, HTMX), UI framework (Bootstrap, Tailwind), Analytics & Marketing (Google Analytics, Facebook Pixel, Hotjar), CDN & infrastruktur (Cloudflare, Google Fonts), IP server, charset, generator tag
- **Usability & Core Web Vitals** — integrasi Google PageSpeed Insights API v5: skor performa Lighthouse, Core Web Vitals dari data lapangan CrUX (LCP, INP, CLS), metrik lab (FCP, TBT, Speed Index), strategi mobile
- **Link Analysis** — struktur link on-page, link friendly/bermakna, estimasi profil backlink berbasis AI
- **SERP Preview & Keyword** — pratinjau snippet hasil pencarian, konsistensi kata kunci di title/description/heading, ekstraksi kata kunci otomatis (single & phrase), estimasi peringkat kata kunci berbasis AI

### AI & Data
- **Rekomendasi AI** — saran perbaikan dari Ollama Cloud API dalam bahasa Indonesia (streaming, markdown)
- **AI Keyword Ranking Estimates** — estimasi potensi peringkat kata kunci berdasarkan analisis konten
- **AI Backlink Estimates** — estimasi profil backlink kompetitif berbasis AI

### Riwayat & Berbagi
- **Riwayat & Permalink** — setiap hasil analisis otomatis tersimpan, bisa diakses via tautan permanen `/r/{id}`
- **Perbandingan URL** — bandingkan dua website secara side-by-side dengan pemenang tiap kategori + analisis AI kompetitif
- **Ekspor PDF** — unduh laporan analisis sebagai PDF (WeasyPrint, fallback print CSS)

### Audit Lanjutan
- **Multi-page Audit** — audit mini hingga 10 URL dari sitemap secara paralel, agregasi isu umum
- **Cek Tambahan** — redirect consistency (www/non-www, http/https), favicon, hreflang, soft-404, page size, response time
- **Generator** — rekomendasi robots.txt, FAQPage JSON-LD, dan llms.txt siap pakai
- **Trend Chart** — grafik perkembangan skor SEO & GEO per domain (SVG server-side)

### Keamanan & Performa
- **Rate Limiting** — proteksi abuse: 10x/menit untuk analyze, 3x/menit untuk multi-page
- **SSRF Guard** — proteksi Server-Side Request Forgery (blokir IP private/loopback)
- **Caching** — cache robots.txt & llms.txt per domain (TTL 10 menit, max 100 entri)

## Tech Stack

- **Backend:** FastAPI + Jinja2 (server-side rendering) + SQLAlchemy async + aiosqlite
- **Frontend:** HTMX (partial reload tanpa JS framework) + CSS murni (Apple-style design)
- **HTTP Client:** httpx (async, connection pooling)
- **Parsing:** BeautifulSoup4 + lxml (HTML), defusedxml (XML safe), Protego (robots.txt)
- **AI:** Ollama Cloud API (streaming chat, competitive analysis, keyword & backlink estimation)
- **Performance:** Google PageSpeed Insights API v5 (Lighthouse + CrUX)
- **Technology Detection:** Signature-based detection (CMS, JS framework, analytics, CDN) dari HTML + headers
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

# === PageSpeed Insights (opsional) ===
# Tanpa API key tetap jalan dengan kuota kecil (~200 request/hari).
# Daftar gratis di https://developers.google.com/speed/docs/insights/v5/get-started
PAGESPEED_API_KEY=your_pagespeed_api_key_here
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
│   ├── main.py                  # Entry point FastAPI (v2.1.0)
│   ├── config.py                # Environment variables via python-dotenv
│   ├── models.py                # Pydantic request/response models
│   ├── models_db.py             # SQLAlchemy ORM (AnalysisRecord)
│   ├── db.py                    # SQLite async engine + session
│   ├── services/
│   │   ├── fetcher.py           # Async HTTP fetcher with SSRF guard & TTL cache
│   │   ├── robots_checker.py    # Analisa robots.txt (Protego + 7 AI crawler)
│   │   ├── sitemap_checker.py   # Analisa sitemap.xml (defusedxml)
│   │   ├── seo_analyzer.py      # Analisa SEO on-page (termasuk keyword extraction)
│   │   ├── geo_analyzer.py      # Analisa GEO readiness
│   │   ├── keyword_analyzer.py  # Ekstraksi & konsistensi kata kunci otomatis
│   │   ├── usability_checker.py # PageSpeed Insights (Lighthouse + CrUX Core Web Vitals)
│   │   ├── technology_checker.py# Deteksi CMS, JS framework, analytics, CDN
│   │   ├── ai_advisor.py        # Ollama Cloud API (streaming chat, keyword & backlink estimation)
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
└── README.md