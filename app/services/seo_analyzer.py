"""
SEO on-page analyzer — checks title, meta, headings, images, links, structured data, etc.
Uses BeautifulSoup4 + lxml for HTML parsing.
"""
import re
import json
from collections import Counter
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

from app.services.keyword_analyzer import extract_keywords


def analyze_seo(html_content: str, target_url: str) -> dict:
    """
    Perform comprehensive on-page SEO analysis.
    
    Returns dict with:
    - score: 0-100 overall SEO score
    - checks: list of individual check results
    - word_count: estimated word count of main content
    - internal_links: count of internal links
    - external_links: count of external links
    """
    if not html_content:
        return {
            "score": 0,
            "checks": [],
            "word_count": 0,
            "internal_links": 0,
            "external_links": 0,
        }

    soup = BeautifulSoup(html_content, "lxml")
    parsed_url = urlparse(target_url)
    domain = parsed_url.netloc

    checks = []
    max_score = 0
    earned_score = 0

    # --- 1. Title Tag ---
    max_score += 10
    title_text = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title_text = title_tag.string.strip()
        title_len = len(title_text)
        if 50 <= title_len <= 60:
            checks.append({
                "name": "Title Tag",
                "status": "good",
                "message": f"Title ditemukan ({title_len} karakter) — panjang ideal.",
                "details": title_text,
            })
            earned_score += 10
        elif 30 <= title_len < 50 or 60 < title_len <= 80:
            checks.append({
                "name": "Title Tag",
                "status": "warning",
                "message": f"Title ditemukan ({title_len} karakter) — idealnya 50-60 karakter.",
                "details": title_text,
            })
            earned_score += 6
        else:
            checks.append({
                "name": "Title Tag",
                "status": "warning",
                "message": f"Title ditemukan tapi panjangnya ({title_len} karakter) di luar rentang optimal.",
                "details": title_text,
            })
            earned_score += 4
    else:
        checks.append({
            "name": "Title Tag",
            "status": "error",
            "message": "Title tag tidak ditemukan — sangat penting untuk SEO.",
        })

    # --- 2. Meta Description ---
    max_score += 10
    desc_text = ""
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta_desc and meta_desc.get("content"):
        desc_text = meta_desc["content"].strip()
        desc_len = len(desc_text)
        if 140 <= desc_len <= 160:
            checks.append({
                "name": "Meta Description",
                "status": "good",
                "message": f"Meta description ditemukan ({desc_len} karakter) — panjang ideal.",
                "details": desc_text[:100] + "..." if len(desc_text) > 100 else desc_text,
            })
            earned_score += 10
        elif 80 <= desc_len < 140 or 160 < desc_len <= 200:
            checks.append({
                "name": "Meta Description",
                "status": "warning",
                "message": f"Meta description ditemukan ({desc_len} karakter) — idealnya 140-160 karakter.",
                "details": desc_text[:100] + "..." if len(desc_text) > 100 else desc_text,
            })
            earned_score += 6
        else:
            checks.append({
                "name": "Meta Description",
                "status": "warning",
                "message": f"Meta description ditemukan tapi panjangnya kurang optimal ({desc_len} karakter).",
                "details": desc_text[:100] + "..." if len(desc_text) > 100 else desc_text,
            })
            earned_score += 4
    else:
        checks.append({
            "name": "Meta Description",
            "status": "error",
            "message": "Meta description tidak ditemukan — mempengaruhi CTR di hasil pencarian.",
        })

    # --- 3. Heading Structure ---
    max_score += 10
    h1_tags = soup.find_all("h1")
    h2_tags = soup.find_all("h2")
    h3_tags = soup.find_all("h3")
    # Must be captured here: the word-count block below decompose()s nav/header/footer,
    # destroying any heading tags inside them.
    headings_text = " ".join(h.get_text(" ", strip=True) for h in h1_tags + h2_tags + h3_tags)

    if len(h1_tags) == 1:
        # Check heading hierarchy
        all_headings = soup.find_all(re.compile(r"^h[1-6]$"))
        hierarchy_ok = True
        prev_level = 0
        for h in all_headings:
            level = int(h.name[1])
            if prev_level > 0 and level > prev_level + 1:
                hierarchy_ok = False
                break
            prev_level = level

        if hierarchy_ok:
            checks.append({
                "name": "Heading Structure",
                "status": "good",
                "message": f"Struktur heading baik: 1 H1, {len(h2_tags)} H2, {len(h3_tags)} H3.",
            })
            earned_score += 10
        else:
            checks.append({
                "name": "Heading Structure",
                "status": "warning",
                "message": f"Ada 1 H1, tapi hierarki heading melompat (misalnya H1 langsung ke H3).",
            })
            earned_score += 6
    elif len(h1_tags) == 0:
        checks.append({
            "name": "Heading Structure",
            "status": "error",
            "message": "Tidak ada H1 tag — setiap halaman sebaiknya punya tepat satu H1.",
        })
    else:
        checks.append({
            "name": "Heading Structure",
            "status": "warning",
            "message": f"Ditemukan {len(h1_tags)} H1 tag — idealnya hanya satu H1 per halaman.",
        })
        earned_score += 4

    # --- 4. Canonical Tag ---
    max_score += 8
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        checks.append({
            "name": "Canonical Tag",
            "status": "good",
            "message": "Canonical tag ditemukan.",
            "details": canonical["href"],
        })
        earned_score += 8
    else:
        checks.append({
            "name": "Canonical Tag",
            "status": "warning",
            "message": "Canonical tag tidak ditemukan — risiko duplikat konten.",
        })

    # --- 5. Meta Viewport ---
    max_score += 8
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport and viewport.get("content"):
        checks.append({
            "name": "Meta Viewport",
            "status": "good",
            "message": "Meta viewport ditemukan — halaman mobile-friendly.",
        })
        earned_score += 8
    else:
        checks.append({
            "name": "Meta Viewport",
            "status": "error",
            "message": "Meta viewport tidak ditemukan — halaman mungkin tidak responsive di mobile.",
        })

    # --- 6. HTTPS ---
    max_score += 8
    if target_url.startswith("https://"):
        checks.append({
            "name": "HTTPS",
            "status": "good",
            "message": "Website menggunakan HTTPS — koneksi aman.",
        })
        earned_score += 8
    else:
        checks.append({
            "name": "HTTPS",
            "status": "error",
            "message": "Website tidak menggunakan HTTPS — sinyal ranking negatif.",
        })

    # --- 7. Image Alt Text ---
    max_score += 10
    images = soup.find_all("img")
    total_images = len(images)
    images_with_alt = sum(1 for img in images if img.get("alt") and img["alt"].strip())

    if total_images == 0:
        checks.append({
            "name": "Image Alt Text",
            "status": "warning",
            "message": "Tidak ada gambar ditemukan di halaman.",
        })
        earned_score += 5
    elif images_with_alt == total_images:
        checks.append({
            "name": "Image Alt Text",
            "status": "good",
            "message": f"Semua {total_images} gambar memiliki alt text.",
        })
        earned_score += 10
    else:
        missing = total_images - images_with_alt
        percentage = round((images_with_alt / total_images) * 100)
        status = "warning" if percentage >= 50 else "error"
        checks.append({
            "name": "Image Alt Text",
            "status": status,
            "message": f"{images_with_alt}/{total_images} gambar memiliki alt text ({percentage}%). {missing} gambar perlu alt text.",
        })
        earned_score += round(10 * (images_with_alt / total_images))

    # --- 8. Open Graph & Twitter Card ---
    max_score += 8
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})
    twitter_card = soup.find("meta", attrs={"name": "twitter:card"})

    og_count = sum(1 for x in [og_title, og_desc, og_image, twitter_card] if x)
    if og_count == 4:
        checks.append({
            "name": "Social Media Tags",
            "status": "good",
            "message": "Open Graph dan Twitter Card tags lengkap.",
        })
        earned_score += 8
    elif og_count >= 2:
        checks.append({
            "name": "Social Media Tags",
            "status": "warning",
            "message": f"Social media tags parsial ({og_count}/4 ditemukan). Lengkapi og:title, og:description, og:image, twitter:card.",
        })
        earned_score += 4
    else:
        checks.append({
            "name": "Social Media Tags",
            "status": "error",
            "message": "Social media tags (Open Graph/Twitter Card) tidak ditemukan atau sangat minim.",
        })

    # --- 9. Structured Data (JSON-LD) ---
    max_score += 10
    json_ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    schema_types = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                if "@type" in data:
                    schema_types.append(data["@type"])
                elif "@graph" in data and isinstance(data["@graph"], list):
                    for item in data["@graph"]:
                        if isinstance(item, dict) and "@type" in item:
                            schema_types.append(item["@type"])
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "@type" in item:
                        schema_types.append(item["@type"])
        except (json.JSONDecodeError, TypeError):
            continue

    if schema_types:
        checks.append({
            "name": "Structured Data",
            "status": "good",
            "message": f"Schema.org JSON-LD ditemukan: {', '.join(set(schema_types))}.",
            "details": list(set(schema_types)),
        })
        earned_score += 10
    else:
        checks.append({
            "name": "Structured Data",
            "status": "warning",
            "message": "Tidak ada structured data (JSON-LD) ditemukan — membantu rich snippets di Google.",
        })

    # --- 10. Word Count ---
    max_score += 8
    # Try to get main content, excluding nav/header/footer
    main_content = soup.find("main") or soup.find("article") or soup.find("body")
    if main_content:
        # Remove nav, header, footer, script, style elements
        for tag in main_content.find_all(["nav", "header", "footer", "script", "style", "noscript"]):
            tag.decompose()
        text = main_content.get_text(separator=" ", strip=True)
        words = len(text.split())
    else:
        text = ""
        words = 0

    if words >= 300:
        checks.append({
            "name": "Jumlah Kata",
            "status": "good",
            "message": f"Konten memiliki ~{words} kata — cukup untuk SEO.",
        })
        earned_score += 8
    elif words >= 100:
        checks.append({
            "name": "Jumlah Kata",
            "status": "warning",
            "message": f"Konten hanya ~{words} kata — idealnya minimal 300 kata.",
        })
        earned_score += 4
    else:
        checks.append({
            "name": "Jumlah Kata",
            "status": "error",
            "message": f"Konten sangat sedikit (~{words} kata) — sulit ranking untuk halaman thin content.",
        })

    # --- 11. Link Analysis ---
    max_score += 10
    all_links = soup.find_all("a", href=True)
    internal_links = 0
    external_links = 0
    nofollow_links = 0
    external_nofollow = 0
    anchor_counts = Counter()
    internal_urls = set()

    for link in all_links:
        href = link["href"]
        if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        parsed_href = urlparse(urljoin(target_url, href))
        is_internal = parsed_href.netloc == domain or not parsed_href.netloc
        is_nofollow = "nofollow" in (link.get("rel") or [])
        if is_nofollow:
            nofollow_links += 1
        anchor = link.get_text(" ", strip=True)[:60]
        if anchor:
            anchor_counts[anchor] += 1
        if is_internal:
            internal_links += 1
            internal_urls.add(parsed_href.path + (f"?{parsed_href.query}" if parsed_href.query else ""))
        else:
            external_links += 1
            if is_nofollow:
                external_nofollow += 1

    # --- Struktur link & friendly URL (informational — tidak mempengaruhi skor) ---
    # ponytail: heuristik naif — query string, underscore, atau path >100 char = tidak friendly
    unfriendly = [u for u in internal_urls if ("?" in u) or ("_" in u) or (len(u) > 100)]
    link_structure = {
        "total": internal_links + external_links,
        "internal": internal_links,
        "external": external_links,
        "nofollow": nofollow_links,
        "dofollow": internal_links + external_links - nofollow_links,
        "external_nofollow": external_nofollow,
        "top_anchors": [{"anchor": a, "count": c} for a, c in anchor_counts.most_common(10)],
    }
    friendly_links = {
        "checked": len(internal_urls),
        "friendly": len(internal_urls) - len(unfriendly),
        "unfriendly_examples": sorted(unfriendly)[:8],
    }

    if internal_links >= 3 and external_links >= 1:
        checks.append({
            "name": "Link Profile",
            "status": "good",
            "message": f"{internal_links} internal links, {external_links} external links — profil link sehat.",
        })
        earned_score += 10
    elif internal_links >= 1:
        checks.append({
            "name": "Link Profile",
            "status": "warning",
            "message": f"{internal_links} internal links, {external_links} external links — pertimbangkan menambah link untuk navigasi dan referensi.",
        })
        earned_score += 5
    else:
        checks.append({
            "name": "Link Profile",
            "status": "error",
            "message": f"Sangat sedikit link ({internal_links} internal, {external_links} external) — halaman terisolasi tidak baik untuk SEO.",
        })

    # --- 12. Keyword Consistency (informational — does not affect score) ---
    keywords = extract_keywords(text, title_text, desc_text, headings_text)

    # Calculate final score
    score = round((earned_score / max_score) * 100) if max_score > 0 else 0

    return {
        "score": score,
        "checks": checks,
        "word_count": words,
        "internal_links": internal_links,
        "external_links": external_links,
        "title": title_text,
        "meta_description": desc_text,
        "keywords": keywords,
        "link_structure": link_structure,
        "friendly_links": friendly_links,
    }


if __name__ == "__main__":
    _html = """<html><head><title>Uji Halaman Struktur Link</title></head><body><main>
    <a href="/produk">Produk</a> <a href="/produk">Produk</a>
    <a href="/cari?q=x&id=1">Cari</a> <a href="/halaman_lama">Lama</a>
    <a href="https://luar.com" rel="nofollow">Luar</a>
    <p>konten konten konten</p></main></body></html>"""
    _r = analyze_seo(_html, "https://situs.id/")
    _ls, _fl = _r["link_structure"], _r["friendly_links"]
    assert _ls["internal"] == 4 and _ls["external"] == 1 and _ls["nofollow"] == 1
    assert _ls["external_nofollow"] == 1 and _ls["dofollow"] == 4
    assert _ls["top_anchors"][0] == {"anchor": "Produk", "count": 2}
    assert _fl["checked"] == 3 and _fl["friendly"] == 1  # query string & underscore = tidak friendly
    print("seo_analyzer link demo OK")
