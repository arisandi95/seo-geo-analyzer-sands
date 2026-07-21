"""
Keyword extraction & consistency — SEOptimer-style auto-extraction from page content.
Pure Python (re + Counter), no new dependencies. Stopwords: Indonesian + English + web noise.
"""
import re
from collections import Counter

STOPWORDS_ID = frozenset("""
yang dan di ke dari ini itu dengan untuk pada adalah dalam tidak akan juga
ada atau bisa kami kita mereka dia ia saya anda kamu telah sudah belum harus
dapat saat ketika karena jika kalau agar supaya namun tetapi tapi serta seperti
yaitu yakni oleh secara antara setelah sebelum sejak hingga sampai masih hanya
lebih sangat paling para bagi tentang terhadap tersebut merupakan menjadi
memiliki melakukan sebagai sebuah salah satu dua tiga banyak semua setiap
sendiri lain lainnya bahwa pun lalu kemudian sehingga walaupun meskipun begitu
demikian hal saja sih deh kok nya apa siapa mana kapan dimana bagaimana mengapa
berapa bukan iya ya tak bila maupun ialah antaranya dll dsb yg dgn utk tsb
""".split())

STOPWORDS_EN = frozenset("""
the a an and or but if of at by for with about against between into through
during before after above below to from up down in out on off over under again
further then once here there when where why how all any both each few more most
other some such no nor not only own same so than too very can will just should
now is are was were be been being have has had do does did this that these
those it its you your we our us they their them he she his her him what which
who whom also get one two new use using may might must shall could would
""".split())

WEB_NOISE = frozenset("""
www com net org http https html menu home beranda login daftar baca klik
selengkapnya berikutnya sebelumnya kembali copyright reserved rights hak cipta
dilindungi cookie share bagikan ikuti follow subscribe langganan search cari
wib wita
""".split())

STOPWORDS = STOPWORDS_ID | STOPWORDS_EN | WEB_NOISE

_TOKEN_RE = re.compile(r"[a-z0-9À-ɏ]{3,}")


def _tokenize(text: str) -> list:
    """Lowercase tokens, >=3 chars, pure numbers dropped."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if not t.isdigit()]


def _presence(term: str, field_lower: str) -> bool:
    """Word-boundary match so 'seo' does not match 'museo'."""
    return bool(re.search(r"\b" + re.escape(term) + r"\b", field_lower))


def _entry(term: str, count: int, title_l: str, desc_l: str, head_l: str) -> dict:
    return {
        "term": term,
        "count": count,
        "in_title": _presence(term, title_l),
        "in_description": _presence(term, desc_l),
        "in_headings": _presence(term, head_l),
    }


def extract_keywords(body_text: str, title: str, description: str,
                     headings_text: str, top_n: int = 8) -> dict:
    """
    Extract top individual keywords and 2-3 word phrases from body text,
    with presence flags against title / meta description / headings.

    Returns {"single": [...], "phrases": [...]}; each entry:
    {"term", "count", "in_title", "in_description", "in_headings"}
    """
    tokens = _tokenize(body_text or "")
    if not tokens:
        return {"single": [], "phrases": []}

    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    head_l = (headings_text or "").lower()

    single_counts = Counter(t for t in tokens if t not in STOPWORDS)
    single = [
        _entry(term, count, title_l, desc_l, head_l)
        for term, count in single_counts.most_common()
        if count >= 2
    ][:top_n]

    # N-grams over the raw token stream (adjacency preserved — stripping stopwords
    # first would fabricate phrases that never appear on the page), then grams
    # containing any stopword are discarded.
    phrase_counts = Counter()
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            gram = tokens[i:i + n]
            if any(t in STOPWORDS for t in gram):
                continue
            phrase_counts[" ".join(gram)] += 1

    top_phrases = sorted(
        ((term, count) for term, count in phrase_counts.items() if count >= 2),
        key=lambda tc: (-tc[1], -len(tc[0])),
    )[:top_n]
    phrases = [_entry(term, count, title_l, desc_l, head_l) for term, count in top_phrases]

    return {"single": single, "phrases": phrases}


def demo():
    body = ("Berita bola hari ini. Berita bola terbaru liga inggris. "
            "Liga inggris pekan ini seru. Berita bola liga inggris.")
    res = extract_keywords(body, "Berita Bola Liga Inggris",
                           "Kumpulan berita bola terkini", "Berita Bola")
    singles = {e["term"]: e for e in res["single"]}
    phrases = {e["term"]: e for e in res["phrases"]}
    assert "berita" in singles and singles["berita"]["in_title"]
    assert "bola" in singles and singles["bola"]["in_description"]
    assert "ini" not in singles  # stopword
    assert "berita bola" in phrases and phrases["berita bola"]["count"] == 3
    assert "liga inggris" in phrases and phrases["liga inggris"]["in_title"]
    assert not phrases["liga inggris"]["in_description"]
    assert extract_keywords("", "t", "d", "h") == {"single": [], "phrases": []}
    print("keyword_analyzer demo OK")


if __name__ == "__main__":
    demo()
