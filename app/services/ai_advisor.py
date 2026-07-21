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

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
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

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": KEYWORD_RANK_PROMPT},
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
