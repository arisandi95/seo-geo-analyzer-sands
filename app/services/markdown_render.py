"""
Markdown → sanitized HTML for AI recommendations.
Audit data itself is always rendered with Jinja2 autoescape; the ONLY thing
rendered as HTML is the AI recommendation, sanitized here with bleach.
"""
import bleach
import markdown

ALLOWED_TAGS = [
    "p", "ul", "ol", "li", "strong", "em",
    "h1", "h2", "h3", "h4", "code", "a",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def render_markdown_safe(text: str) -> str:
    """Convert markdown text to HTML, then strip everything outside the whitelist."""
    html = markdown.markdown(text or "", extensions=["extra", "sane_lists"])
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
