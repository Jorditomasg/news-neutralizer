"""URL normalization and deduplication utilities."""

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import re


# Tracking / analytics query parameters to strip
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_cid", "utm_reader", "utm_referrer",
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid",
    "ref", "referer", "referrer",
    "mc_cid", "mc_eid",
    "_ga", "_gl", "_hsenc", "_hsmi",
    "source", "src",
    "ncid", "nr_email_referer",
    "s_cid", "s_kwcid",
    "wickedid", "twclid",
}


def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison purposes:
    - Lowercase scheme and host
    - Strip tracking query parameters
    - Remove fragments
    - Remove trailing slashes from path
    - Normalize www. prefix (remove it)
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)
    except Exception:
        return url

    # Force HTTPS scheme and lowercase host
    scheme = "https"
    netloc = parsed.netloc.lower()

    # Remove www. prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Clean path: remove trailing slash (but keep "/" for root)
    path = parsed.path.rstrip("/") or "/"

    # Filter query params: remove tracking params
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        clean_params = {
            k: v for k, v in params.items()
            if k.lower() not in _TRACKING_PARAMS
        }
        query = urlencode(clean_params, doseq=True) if clean_params else ""
    else:
        query = ""

    # Remove fragment
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def extract_domain(url: str) -> str:
    """Extract the clean domain from a URL (without www., m., mobile.)."""
    try:
        netloc = urlparse(url).netloc.lower()
        for prefix in ("www.", "m.", "mobile.", "amp."):
            if netloc.startswith(prefix):
                netloc = netloc[len(prefix):]
        return netloc
    except Exception:
        return ""


def urls_match(url1: str, url2: str) -> bool:
    """Check if two URLs point to the same resource after normalization."""
    return normalize_url(url1) == normalize_url(url2)


def is_google_news_url(url: str) -> bool:
    """Check if a URL is a Google News redirect/article URL."""
    try:
        parsed = urlparse(url)
        return "news.google.com" in parsed.netloc.lower()
    except Exception:
        return False
