"""
Technology Results — deteksi teknologi website dari HTML + response headers.
Wappalyzer-style signature matching, pure Python, tanpa API eksternal.
ponytail: signature list kecil (teknologi populer saja), bukan database Wappalyzer penuh.
"""
import asyncio
import re
import socket
from urllib.parse import urlparse

# (kategori, nama, regex pada HTML mentah)
_SIGNATURES = [
    ("CMS", "WordPress", r"wp-content/|wp-includes/|/wp-json"),
    ("CMS", "Joomla", r"/media/jui/|content=[\"']Joomla"),
    ("CMS", "Drupal", r"Drupal\.settings|/sites/default/files"),
    ("CMS", "Blogger", r"blogger\.com/static|\.blogspot\."),
    ("CMS", "Wix", r"static\.parastorage\.com"),
    ("E-commerce", "Shopify", r"cdn\.shopify\.com"),
    ("E-commerce", "WooCommerce", r"woocommerce"),
    ("JavaScript", "jQuery", r"jquery[.-][\w.]*\.js"),
    ("JavaScript", "React", r"react(?:\.production|\.development|-dom)[\w.]*\.js|data-reactroot"),
    ("JavaScript", "Next.js", r"__NEXT_DATA__|/_next/"),
    ("JavaScript", "Vue.js", r"vue(?:\.runtime)?(?:\.min)?\.js|\sdata-v-[0-9a-f]{8}"),
    ("JavaScript", "Nuxt", r"__NUXT__|/_nuxt/"),
    ("JavaScript", "Angular", r"\sng-version="),
    ("JavaScript", "Alpine.js", r"alpine(?:\.min)?\.js"),
    ("JavaScript", "HTMX", r"htmx(?:\.min)?\.js|\shx-(?:get|post|swap)="),
    ("UI Framework", "Bootstrap", r"bootstrap(?:\.bundle)?(?:\.min)?\.(?:css|js)"),
    ("UI Framework", "Tailwind CSS", r"cdn\.tailwindcss\.com|tailwind(?:\.min)?\.css"),
    ("UI Framework", "Font Awesome", r"font-?awesome"),
    ("Analytics & Marketing", "Google Analytics", r"google-analytics\.com|gtag\("),
    ("Analytics & Marketing", "Google Tag Manager", r"googletagmanager\.com"),
    ("Analytics & Marketing", "Facebook Pixel", r"connect\.facebook\.net|fbq\("),
    ("Analytics & Marketing", "Hotjar", r"static\.hotjar\.com"),
    ("Analytics & Marketing", "Google AdSense", r"adsbygoogle|pagead2\.googlesyndication"),
    ("CDN & Infrastruktur", "Cloudflare CDN", r"cdnjs\.cloudflare\.com"),
    ("CDN & Infrastruktur", "jsDelivr", r"cdn\.jsdelivr\.net"),
    ("CDN & Infrastruktur", "unpkg", r"unpkg\.com"),
    ("CDN & Infrastruktur", "Google Fonts", r"fonts\.googleapis\.com|fonts\.gstatic\.com"),
]

_CATEGORY_ORDER = ["CMS", "E-commerce", "JavaScript", "UI Framework",
                   "Analytics & Marketing", "CDN & Infrastruktur"]

_GENERATOR_RE = re.compile(r"<meta[^>]+name=[\"']generator[\"'][^>]+content=[\"']([^\"']+)", re.I)
_GENERATOR_RE_REV = re.compile(r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+name=[\"']generator[\"']", re.I)
_CHARSET_RE = re.compile(r"<meta[^>]+charset=[\"']?([\w-]+)", re.I)


async def _resolve_ip(hostname: str):
    """IP pertama hostname (prefer IPv4); None jika gagal."""
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError):
        return None
    ips = [i[4][0] for i in infos]
    return next((ip for ip in ips if ":" not in ip), ips[0] if ips else None)


def _detect(html_content: str, html_headers: dict) -> dict:
    found = {}  # (category, name) → True, preserves insertion order
    for category, name, pattern in _SIGNATURES:
        if re.search(pattern, html_content, re.I):
            found[(category, name)] = True

    headers = {k.lower(): v for k, v in (html_headers or {}).items()}
    if "cf-ray" in headers:
        found[("CDN & Infrastruktur", "Cloudflare")] = True

    generator = None
    m = _GENERATOR_RE.search(html_content) or _GENERATOR_RE_REV.search(html_content)
    if m:
        generator = m.group(1).strip()[:80]

    charset = None
    m = _CHARSET_RE.search(html_content)
    if m:
        charset = m.group(1).upper()
    elif "charset=" in headers.get("content-type", "").lower():
        charset = headers["content-type"].lower().split("charset=")[-1].split(";")[0].strip().upper()

    # Kelompokkan per kategori sesuai urutan tetap
    grouped = []
    for cat in _CATEGORY_ORDER:
        names = [name for (c, name) in found if c == cat]
        if names:
            grouped.append({"category": cat, "names": names})

    return {
        "detected": grouped,                              # [{"category", "names": [...]}]
        "total": sum(len(g["names"]) for g in grouped),
        "generator": generator,
        "server": headers.get("server", "").strip()[:80] or None,
        "powered_by": headers.get("x-powered-by", "").strip()[:80] or None,
        "charset": charset,
    }


async def analyze_technology(html_content: str, html_headers: dict, target_url: str) -> dict:
    """
    Deteksi teknologi dari HTML + headers, plus resolve IP server. Never raises.
    Returns {"detected", "total", "generator", "server", "powered_by", "charset", "ip"}.
    """
    try:
        result = _detect(html_content or "", html_headers or {})
    except Exception:
        result = {"detected": [], "total": 0, "generator": None,
                  "server": None, "powered_by": None, "charset": None}
    hostname = urlparse(target_url).hostname
    result["ip"] = await _resolve_ip(hostname) if hostname else None
    return result


def demo():
    html = """<html><head><meta charset="utf-8">
    <meta name="generator" content="WordPress 6.4.2">
    <link href="/wp-content/themes/x/style.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet">
    <script src="/wp-includes/js/jquery/jquery.min.js"></script>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-X"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/js/bootstrap.bundle.min.js"></script>
    </head><body></body></html>"""
    r = _detect(html, {"server": "nginx/1.18.0", "x-powered-by": "PHP/8.1", "cf-ray": "abc"})
    cats = {g["category"]: g["names"] for g in r["detected"]}
    assert "WordPress" in cats["CMS"]
    assert "jQuery" in cats["JavaScript"]
    assert "Bootstrap" in cats["UI Framework"]
    assert "Google Tag Manager" in cats["Analytics & Marketing"]
    assert "Cloudflare" in cats["CDN & Infrastruktur"] and "jsDelivr" in cats["CDN & Infrastruktur"]
    assert r["generator"] == "WordPress 6.4.2"
    assert r["server"] == "nginx/1.18.0" and r["powered_by"] == "PHP/8.1"
    assert r["charset"] == "UTF-8"
    assert r["total"] >= 7
    empty = _detect("", {})
    assert empty["detected"] == [] and empty["total"] == 0 and empty["charset"] is None
    print("technology_checker demo OK")


if __name__ == "__main__":
    demo()
