"""
Usability — Google PageSpeed Insights API v5 (skor performa + Core Web Vitals).
Satu call mendapatkan lab data (Lighthouse) dan field data (CrUX) sekaligus.
Tanpa API key tetap jalan (kuota kecil); PAGESPEED_API_KEY opsional untuk kuota besar.
"""
import httpx

from app.config import settings

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# (key CrUX, label, formatter percentile)
_FIELD_METRICS = [
    ("LARGEST_CONTENTFUL_PAINT_MS", "LCP", lambda p: f"{p / 1000:.1f} s"),
    ("INTERACTION_TO_NEXT_PAINT", "INP", lambda p: f"{p:.0f} ms"),
    ("CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS", lambda p: f"{p / 100:.2f}"),
]
_FIELD_CATEGORY_CLASS = {"FAST": "good", "AVERAGE": "warning", "SLOW": "error"}

# (key audit Lighthouse, label)
_LAB_AUDITS = [
    ("first-contentful-paint", "First Contentful Paint"),
    ("largest-contentful-paint", "Largest Contentful Paint"),
    ("cumulative-layout-shift", "Cumulative Layout Shift"),
    ("total-blocking-time", "Total Blocking Time"),
    ("speed-index", "Speed Index"),
]

_PSI_EMPTY = {"performance_score": None, "field": None, "lab": []}


def _score_class(score) -> str:
    if score is None:
        return "warning"
    return "good" if score >= 0.9 else ("warning" if score >= 0.5 else "error")


def _parse_psi(data: dict) -> dict:
    lh = data.get("lighthouseResult") or {}

    raw_score = ((lh.get("categories") or {}).get("performance") or {}).get("score")
    performance_score = round(raw_score * 100) if raw_score is not None else None

    audits = lh.get("audits") or {}
    lab = []
    for key, label in _LAB_AUDITS:
        audit = audits.get(key) or {}
        value = audit.get("displayValue")
        if value:
            lab.append({
                "name": label,
                "value": value,
                "status": _score_class(audit.get("score")),
            })

    field = None
    loading = data.get("loadingExperience") or {}
    metrics = loading.get("metrics") or {}
    field_rows = []
    for key, label, fmt in _FIELD_METRICS:
        m = metrics.get(key)
        if not m or m.get("percentile") is None:
            continue
        category = str(m.get("category", "")).upper()
        field_rows.append({
            "name": label,
            "value": fmt(m["percentile"]),
            "category": category,
            "status": _FIELD_CATEGORY_CLASS.get(category, "warning"),
        })
    if field_rows:
        field = {
            "overall": str(loading.get("overall_category", "")).upper() or None,
            "metrics": field_rows,
        }

    return {"performance_score": performance_score, "field": field, "lab": lab}


async def get_pagespeed_data(url: str) -> dict:
    """
    Run PageSpeed Insights (strategy=mobile). Never raises.
    Returns {"available": bool, "note": str|None, "strategy": "mobile",
             "performance_score": int|None,
             "field": {"overall", "metrics": [{name,value,category,status}]} | None,
             "lab": [{name,value,status}]}
    """
    params = {"url": url, "strategy": "mobile", "category": "performance"}
    if settings.PAGESPEED_API_KEY:
        params["key"] = settings.PAGESPEED_API_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.get(PSI_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                note = "⚠️ Kuota PageSpeed API terlampaui (429). Tambahkan PAGESPEED_API_KEY (gratis) di `.env` untuk kuota lebih besar."
            elif e.response.status_code == 400:
                note = "⚠️ PageSpeed tidak dapat menganalisa URL ini (400) — halaman mungkin tidak dapat diakses publik."
            else:
                note = f"⚠️ PageSpeed API error: {e.response.status_code}"
            return {"available": False, "note": note, "strategy": "mobile", **_PSI_EMPTY}
        except httpx.TimeoutException:
            return {"available": False, "note": "⚠️ PageSpeed Insights timeout (analisa Lighthouse bisa lama). Coba lagi beberapa saat.", "strategy": "mobile", **_PSI_EMPTY}
        except Exception as e:
            return {"available": False, "note": f"⚠️ Gagal mengambil data PageSpeed: {str(e)}", "strategy": "mobile", **_PSI_EMPTY}

    try:
        parsed = _parse_psi(data)
    except Exception:
        return {"available": False, "note": "⚠️ Format respons PageSpeed tidak dikenali.", "strategy": "mobile", **_PSI_EMPTY}

    if parsed["performance_score"] is None and not parsed["lab"] and not parsed["field"]:
        return {"available": False, "note": "⚠️ PageSpeed tidak mengembalikan data untuk URL ini.", "strategy": "mobile", **_PSI_EMPTY}
    return {"available": True, "note": None, "strategy": "mobile", **parsed}


def demo():
    sample = {
        "lighthouseResult": {
            "categories": {"performance": {"score": 0.87}},
            "audits": {
                "largest-contentful-paint": {"displayValue": "2.4 s", "score": 0.91},
                "cumulative-layout-shift": {"displayValue": "0.02", "score": 0.99},
                "total-blocking-time": {"displayValue": "310 ms", "score": 0.55},
                "first-contentful-paint": {"displayValue": "1.2 s", "score": 0.95},
                "speed-index": {"displayValue": "3.1 s", "score": 0.4},
            },
        },
        "loadingExperience": {
            "overall_category": "AVERAGE",
            "metrics": {
                "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 2600, "category": "AVERAGE"},
                "INTERACTION_TO_NEXT_PAINT": {"percentile": 150, "category": "FAST"},
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 8, "category": "FAST"},
            },
        },
    }
    p = _parse_psi(sample)
    assert p["performance_score"] == 87
    assert len(p["lab"]) == 5 and p["lab"][0]["status"] == "good" and p["lab"][4]["status"] == "error"
    assert p["field"]["overall"] == "AVERAGE"
    lcp, inp, cls_ = p["field"]["metrics"]
    assert lcp == {"name": "LCP", "value": "2.6 s", "category": "AVERAGE", "status": "warning"}
    assert inp["value"] == "150 ms" and inp["status"] == "good"
    assert cls_["value"] == "0.08"
    assert _parse_psi({}) == {"performance_score": None, "field": None, "lab": []}
    print("usability_checker demo OK")


if __name__ == "__main__":
    demo()
