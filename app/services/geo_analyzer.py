"""
GEO (Generative Engine Optimization) analyzer.
"""
import re
import json
from bs4 import BeautifulSoup

QUESTION_PATTERNS = re.compile(
    r"^(apa|bagaimana|mengapa|kapan|dimana|di mana|siapa|berapa|"
    r"what|how|why|when|where|who|which|can|does|do|is|are|will|should)\b",
    re.IGNORECASE
)


def analyze_geo(html_content: str, robots_result: dict, llms_txt_content: str = None) -> dict:
    if not html_content:
        return {"score": 0, "checks": []}

    soup = BeautifulSoup(html_content, "lxml")
    checks = []
    total_weight = 0
    earned_weight = 0

    # 1. AI Crawler Access (weight: 25)
    weight = 25
    total_weight += weight
    ai_access = robots_result.get("ai_crawler_access", {})
    if ai_access:
        allowed_count = sum(1 for v in ai_access.values() if v)
        total_bots = len(ai_access)
        if allowed_count == total_bots:
            checks.append({"name": "Akses AI Crawler", "status": "good",
                "message": f"Semua {total_bots} AI crawler diizinkan mengakses konten.", "weight": weight})
            earned_weight += weight
        elif allowed_count > 0:
            blocked = [k for k, v in ai_access.items() if not v]
            checks.append({"name": "Akses AI Crawler", "status": "warning",
                "message": f"{allowed_count}/{total_bots} AI crawler diizinkan. Diblokir: {', '.join(blocked)}.", "weight": weight})
            earned_weight += weight * (allowed_count / total_bots)
        else:
            checks.append({"name": "Akses AI Crawler", "status": "error",
                "message": "Semua AI crawler diblokir — konten tidak akan bisa dikutip oleh AI.", "weight": weight})
    else:
        checks.append({"name": "Akses AI Crawler", "status": "good",
            "message": "Tidak ada pembatasan untuk AI crawler.", "weight": weight})
        earned_weight += weight

    # 2. FAQ/QA Structured Data (weight: 20)
    weight = 20
    total_weight += weight
    json_ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    faq_found = False
    qa_types = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            schemas = _extract_types(data)
            for s in schemas:
                if s in ("FAQPage", "QAPage", "Question"):
                    faq_found = True
                    qa_types.append(s)
        except (json.JSONDecodeError, TypeError):
            continue
    if faq_found:
        checks.append({"name": "FAQ/QA Schema", "status": "good",
            "message": f"Schema Q&A ditemukan: {', '.join(set(qa_types))} — sinyal kuat untuk AI.", "weight": weight})
        earned_weight += weight
    else:
        checks.append({"name": "FAQ/QA Schema", "status": "warning",
            "message": "Tidak ada FAQ/QA schema — tambahkan FAQPage untuk meningkatkan peluang dikutip AI.", "weight": weight})

    # 3. Question-Based Headings (weight: 15)
    weight = 15
    total_weight += weight
    headings = soup.find_all(["h2", "h3"])
    q_headings = [h.get_text(strip=True) for h in headings if QUESTION_PATTERNS.match(h.get_text(strip=True)) or h.get_text(strip=True).endswith("?")]
    total_h = len(headings)
    if total_h > 0 and len(q_headings) >= 2:
        checks.append({"name": "Heading Berbasis Pertanyaan", "status": "good",
            "message": f"{len(q_headings)}/{total_h} heading berbentuk pertanyaan — bagus untuk AI chunking.", "weight": weight})
        earned_weight += weight
    elif len(q_headings) >= 1:
        checks.append({"name": "Heading Berbasis Pertanyaan", "status": "warning",
            "message": f"Hanya {len(q_headings)} heading berbentuk pertanyaan. Tambahkan lebih banyak.", "weight": weight})
        earned_weight += weight * 0.5
    else:
        checks.append({"name": "Heading Berbasis Pertanyaan", "status": "warning",
            "message": f"Tidak ada heading pertanyaan dari {total_h} heading. Konten Q&A lebih mudah dikutip AI.", "weight": weight})

    # 4. Author/E-E-A-T Signals (weight: 15)
    weight = 15
    total_weight += weight
    author_signals = _count_author_signals(soup, json_ld_scripts)
    if author_signals >= 2:
        checks.append({"name": "Author/E-E-A-T", "status": "good",
            "message": "Sinyal author/E-E-A-T kuat — AI memprioritaskan konten dengan sumber terpercaya.", "weight": weight})
        earned_weight += weight
    elif author_signals >= 1:
        checks.append({"name": "Author/E-E-A-T", "status": "warning",
            "message": "Sinyal author ditemukan tapi bisa diperkuat.", "weight": weight})
        earned_weight += weight * 0.5
    else:
        checks.append({"name": "Author/E-E-A-T", "status": "error",
            "message": "Tidak ada sinyal author/E-E-A-T — AI cenderung melewatkan konten tanpa sumber jelas.", "weight": weight})

    # 5. Statistics/Data (weight: 10)
    weight = 10
    total_weight += weight
    paragraphs = soup.find_all("p")
    first_text = " ".join(p.get_text(strip=True) for p in paragraphs[:5])
    stats = len(re.findall(r"\d+[\.,]?\d*\s*(%|persen|percent|juta|miliar|ribu|million|billion)?", first_text, re.I))
    if stats >= 3:
        checks.append({"name": "Data & Statistik", "status": "good",
            "message": f"{stats} data/angka di paragraf awal — AI suka mengutip data konkret.", "weight": weight})
        earned_weight += weight
    elif stats >= 1:
        checks.append({"name": "Data & Statistik", "status": "warning",
            "message": f"Hanya {stats} data/angka di paragraf awal. Tambahkan lebih banyak.", "weight": weight})
        earned_weight += weight * 0.5
    else:
        checks.append({"name": "Data & Statistik", "status": "warning",
            "message": "Tidak ada angka/statistik di paragraf awal.", "weight": weight})

    # 6. Content Freshness (weight: 10)
    weight = 10
    total_weight += weight
    fresh = _check_freshness(soup, json_ld_scripts)
    if fresh:
        checks.append({"name": "Freshness Indicator", "status": "good",
            "message": "Tanggal publish/update ditemukan — AI memprioritaskan konten terbaru.", "weight": weight})
        earned_weight += weight
    else:
        checks.append({"name": "Freshness Indicator", "status": "warning",
            "message": "Tidak ada tanggal publish/update eksplisit.", "weight": weight})

    # 7. llms.txt (weight: 5)
    weight = 5
    total_weight += weight
    if llms_txt_content:
        checks.append({"name": "llms.txt", "status": "good",
            "message": "File llms.txt ditemukan — ringkasan konten untuk AI crawler.", "weight": weight})
        earned_weight += weight
    else:
        checks.append({"name": "llms.txt", "status": "warning",
            "message": "File llms.txt tidak ditemukan (standar baru, bersifat informasional).", "weight": weight})

    score = round((earned_weight / total_weight) * 100) if total_weight > 0 else 0
    return {"score": score, "checks": checks}


def _extract_types(data):
    types = []
    if isinstance(data, dict):
        if "@type" in data:
            types.append(data["@type"])
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                if isinstance(item, dict) and "@type" in item:
                    types.append(item["@type"])
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "@type" in item:
                types.append(item["@type"])
    return types


def _count_author_signals(soup, json_ld_scripts):
    signals = 0
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            s = json.dumps(data)
            if '"Person"' in s or '"Organization"' in s:
                signals += 1
                break
        except (json.JSONDecodeError, TypeError):
            continue
    if soup.find("a", attrs={"rel": "author"}) or soup.find("link", attrs={"rel": "author"}):
        signals += 1
    if soup.find("meta", attrs={"name": "author"}):
        signals += 1
    return signals


def _check_freshness(soup, json_ld_scripts):
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            s = json.dumps(data)
            if "datePublished" in s or "dateModified" in s:
                return True
        except (json.JSONDecodeError, TypeError):
            continue
    if soup.find_all("time"):
        return True
    return False
