"""
AI Advisor — integrates with Ollama Cloud API for recommendations.
"""
import httpx
import json
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
