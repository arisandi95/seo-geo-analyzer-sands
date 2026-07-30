"""
AI Advisor — integrates with Ollama Cloud API for recommendations.
"""
import httpx
import json
import re
from app.config import settings

SYSTEM_PROMPT = """Kamu adalah konsultan SEO dan GEO (Generative Engine Optimization) profesional.
Kamu akan menerima data hasil audit teknis sebuah website dalam format JSON (mencakup analisa
robots.txt, sitemap, SEO on-page, dan GEO readiness). Tugasmu:
1. Berikan ringkasan kondisi website (2-3 kalimat).
2. Berikan 5 rekomendasi perbaikan paling prioritas, urutkan dari dampak terbesar.
3. Untuk tiap rekomendasi, jelaskan alasannya secara singkat dan actionable.
4. Gunakan bahasa Indonesia yang jelas, hindari jargon berlebihan.
5. Jangan mengarang data yang tidak ada di JSON yang diberikan.
Format output dalam markdown dengan heading dan bullet list."""


async def get_ai_recommendations(audit_data: dict) -> str:
    """
    Send audit data to Ollama Cloud API and get AI recommendations.
    Never blocks the main result — returns fallback message on any error.
    """
    if not settings.OLLAMA_API_KEY or settings.OLLAMA_API_KEY == "your_ollama_cloud_api_key_here":
        return "⚠️ API key Ollama belum dikonfigurasi. Masukkan API key di file `.env` untuk mendapatkan rekomendasi AI."

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(audit_data, ensure_ascii=False, default=str)},
        ],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    is_openai = settings.OLLAMA_BASE_URL.rstrip("/").endswith("v1")
    endpoint = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/chat/completions" if is_openai else f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] if is_openai else data["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return "⚠️ Gagal terhubung ke Ollama Cloud: API key tidak valid atau kadaluarsa."
            return f"⚠️ Ollama API error: {e.response.status_code}"
        except httpx.TimeoutException:
            return "⚠️ Permintaan ke AI advisor timeout. Coba lagi beberapa saat."
        except Exception as e:
            return f"⚠️ Gagal mendapatkan rekomendasi AI: {str(e)}"


KEYWORD_RANK_PROMPT = """Kamu adalah pakar SEO. Berdasarkan data halaman (title, meta description, url,
keyword hasil ekstraksi beserta frekuensi), perkirakan maksimal 8 keyword yang paling mungkin membuat
halaman ini muncul di pencarian Google Indonesia. Ini ESTIMASI, bukan data ranking real.
Jawab HANYA JSON valid tanpa teks lain, format:
{"estimates":[{"keyword":"...","opportunity":"tinggi|sedang|rendah","position":"1-10|11-30|31-50|50+","reason":"alasan singkat 1 kalimat"}]}"""

_OPPORTUNITIES = {"tinggi", "sedang", "rendah"}


def _extract_json_object(text: str):
    """Salvage a JSON object from LLM output (may contain <think> blocks or ``` fences)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = text.replace("```json", "").replace("```", "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def get_keyword_estimates(audit_data: dict) -> dict:
    """
    Estimate likely-ranking keywords via Ollama Cloud (AI estimation — NOT real SERP data).
    Never raises. Returns {"available": bool, "note": str|None, "estimates": [...]};
    each estimate: {"keyword", "opportunity", "position", "reason"}.
    """
    seo = audit_data.get("seo") or {}
    kw = seo.get("keywords") or {}
    payload_data = {
        "url": audit_data.get("url", ""),
        "title": seo.get("title", ""),
        "meta_description": seo.get("meta_description", ""),
        "keywords_single": [{"term": e["term"], "count": e["count"]} for e in kw.get("single", [])],
        "keywords_phrases": [{"term": e["term"], "count": e["count"]} for e in kw.get("phrases", [])],
    }

    if not payload_data["title"] and not payload_data["keywords_single"] and not payload_data["keywords_phrases"]:
        return {"available": False, "note": "Tidak cukup konten untuk estimasi keyword.", "estimates": []}

    if not settings.OLLAMA_API_KEY or settings.OLLAMA_API_KEY == "your_ollama_cloud_api_key_here":
        return {
            "available": False,
            "note": "⚠️ API key Ollama belum dikonfigurasi. Masukkan API key di file `.env` untuk mendapatkan estimasi keyword.",
            "estimates": [],
        }

    is_openai = settings.OLLAMA_BASE_URL.rstrip("/").endswith("v1")
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": KEYWORD_RANK_PROMPT},
            {"role": "user", "content": json.dumps(payload_data, ensure_ascii=False)},
        ],
        "stream": False,
    }
    if is_openai:
        payload["response_format"] = {"type": "json_object"}
    else:
        payload["format"] = "json"
    headers = {
        "Authorization": f"Bearer {settings.OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            endpoint = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/chat/completions" if is_openai else f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
            resp = await client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"] if is_openai else data["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"available": False, "note": "⚠️ Gagal terhubung ke Ollama Cloud: API key tidak valid atau kadaluarsa.", "estimates": []}
            return {"available": False, "note": f"⚠️ Ollama API error: {e.response.status_code}", "estimates": []}
        except httpx.TimeoutException:
            return {"available": False, "note": "⚠️ Permintaan estimasi keyword timeout. Coba lagi beberapa saat.", "estimates": []}
        except Exception as e:
            return {"available": False, "note": f"⚠️ Gagal mendapatkan estimasi keyword: {str(e)}", "estimates": []}

    parsed = _extract_json_object(content)
    raw_items = parsed.get("estimates") if parsed else None
    estimates = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword", "")).strip()[:80]
        if not keyword:
            continue
        opportunity = str(item.get("opportunity", "")).strip().lower()
        if opportunity not in _OPPORTUNITIES:
            opportunity = "sedang"
        estimates.append({
            "keyword": keyword,
            "opportunity": opportunity,
            "position": str(item.get("position", "-")).strip()[:20],
            "reason": str(item.get("reason", "")).strip()[:200],
        })
        if len(estimates) >= 10:
            break

    if not estimates:
        return {"available": False, "note": "⚠️ AI tidak mengembalikan estimasi yang valid. Coba analisa ulang.", "estimates": []}
    return {"available": True, "note": None, "estimates": estimates}


BACKLINK_PROMPT = """Kamu adalah pakar SEO off-page. Berdasarkan data halaman (url, title, meta description,
keyword utama, struktur link on-page), berikan PERKIRAAN kualitatif profil backlink untuk domain ini.
Ini ESTIMASI dari konten halaman, BUKAN data backlink real — DILARANG mengarang angka jumlah backlink.
Jawab HANYA JSON valid tanpa teks lain, format:
{"summary":{"level":"rendah|sedang|tinggi","reason":"1 kalimat kenapa"},
"top_pages":[{"page":"path atau url di domain ini","reason":"kenapa halaman ini berpeluang menarik backlink"}],
"top_anchors":[{"anchor":"...","type":"branded|keyword|generic"}],
"geographies":[{"country":"...","share":"dominan|sedang|kecil"}]}
Maksimal 5 item untuk top_pages dan top_anchors, 3 untuk geographies."""

_LEVELS = {"rendah", "sedang", "tinggi"}
_SHARES = {"dominan", "sedang", "kecil"}
_ANCHOR_TYPES = {"branded", "keyword", "generic"}

_BACKLINK_EMPTY = {"summary": None, "top_pages": [], "top_anchors": [], "geographies": []}


async def get_backlink_estimates(audit_data: dict) -> dict:
    """
    Qualitative backlink-profile estimate via Ollama Cloud (AI estimation — NOT real
    backlink index data). Never raises.
    Returns {"available": bool, "note": str|None, "summary": {...}|None,
             "top_pages": [...], "top_anchors": [...], "geographies": [...]}.
    """
    seo = audit_data.get("seo") or {}
    kw = seo.get("keywords") or {}
    ls = seo.get("link_structure") or {}
    payload_data = {
        "url": audit_data.get("url", ""),
        "title": seo.get("title", ""),
        "meta_description": seo.get("meta_description", ""),
        "keywords": [e["term"] for e in (kw.get("single") or [])[:5]],
        "link_structure": {
            "internal": ls.get("internal", 0),
            "external": ls.get("external", 0),
            "top_anchors": [a["anchor"] for a in (ls.get("top_anchors") or [])[:5]],
        },
    }

    if not payload_data["title"] and not payload_data["keywords"]:
        return {"available": False, "note": "Tidak cukup konten untuk estimasi profil backlink.", **_BACKLINK_EMPTY}

    if not settings.OLLAMA_API_KEY or settings.OLLAMA_API_KEY == "your_ollama_cloud_api_key_here":
        return {
            "available": False,
            "note": "⚠️ API key Ollama belum dikonfigurasi. Masukkan API key di file `.env` untuk mendapatkan estimasi profil backlink.",
            **_BACKLINK_EMPTY,
        }

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": BACKLINK_PROMPT},
            {"role": "user", "content": json.dumps(payload_data, ensure_ascii=False)},
        ],
        "stream": False,
        "format": "json",
    }
    headers = {
        "Authorization": f"Bearer {settings.OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"available": False, "note": "⚠️ Gagal terhubung ke Ollama Cloud: API key tidak valid atau kadaluarsa.", **_BACKLINK_EMPTY}
            return {"available": False, "note": f"⚠️ Ollama API error: {e.response.status_code}", **_BACKLINK_EMPTY}
        except httpx.TimeoutException:
            return {"available": False, "note": "⚠️ Permintaan estimasi backlink timeout. Coba lagi beberapa saat.", **_BACKLINK_EMPTY}
        except Exception as e:
            return {"available": False, "note": f"⚠️ Gagal mendapatkan estimasi backlink: {str(e)}", **_BACKLINK_EMPTY}

    parsed = _extract_json_object(content) or {}

    raw_summary = parsed.get("summary")
    summary = None
    if isinstance(raw_summary, dict):
        level = str(raw_summary.get("level", "")).strip().lower()
        summary = {
            "level": level if level in _LEVELS else "sedang",
            "reason": str(raw_summary.get("reason", "")).strip()[:200],
        }

    def _clean_list(key, fields, limit, norm_field=None, norm_set=None, norm_default=""):
        out = []
        for item in parsed.get(key) or []:
            if not isinstance(item, dict):
                continue
            row = {f: str(item.get(f, "")).strip()[:120] for f in fields}
            if not row[fields[0]]:
                continue
            if norm_field:
                val = row[norm_field].lower()
                row[norm_field] = val if val in norm_set else norm_default
            out.append(row)
            if len(out) >= limit:
                break
        return out

    top_pages = _clean_list("top_pages", ("page", "reason"), 5)
    top_anchors = _clean_list("top_anchors", ("anchor", "type"), 5, "type", _ANCHOR_TYPES, "generic")
    geographies = _clean_list("geographies", ("country", "share"), 4, "share", _SHARES, "sedang")

    if not summary and not top_pages and not top_anchors and not geographies:
        return {"available": False, "note": "⚠️ AI tidak mengembalikan estimasi yang valid. Coba analisa ulang.", **_BACKLINK_EMPTY}
    return {
        "available": True,
        "note": None,
        "summary": summary,
        "top_pages": top_pages,
        "top_anchors": top_anchors,
        "geographies": geographies,
    }
