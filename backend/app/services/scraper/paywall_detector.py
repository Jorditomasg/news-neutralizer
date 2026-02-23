"""Heuristic paywall/truncated content detector.

Detects whether an article's content has been truncated by a paywall
using pure pattern matching — no LLM calls needed.
Multilingual: supports Spanish, English, French, Portuguese, Italian, German.
"""

import re
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)

# ── Paywall keyword patterns (multilingual) ──────────────────
# Each tuple: (pattern, language_hint)
_PAYWALL_PHRASES: list[str] = [
    # Spanish
    r"suscr[íi]bete",
    r"para seguir leyendo",
    r"contenido exclusivo",
    r"hazte premium",
    r"accede al contenido completo",
    r"solo para suscriptores",
    r"art[íi]culo de pago",
    r"inicia sesi[óo]n para",
    r"reg[íi]strate para",
    r"contenido para abonados",
    r"este contenido es .{0,20}suscriptores",
    r"suscripci[óo]n",
    # English
    r"subscribe to",
    r"to continue reading",
    r"exclusive content",
    r"premium content",
    r"sign in to read",
    r"log in to continue",
    r"subscribers only",
    r"become a member",
    r"unlock this article",
    r"create (?:a )?free account",
    r"already a subscriber",
    # French
    r"r[ée]serv[ée] aux abonn[ée]s",
    r"abonnez-vous",
    r"contenu r[ée]serv[ée]",
    r"pour continuer [àa] lire",
    r"acc[ée]dez [àa] l'ensemble",
    # Portuguese
    r"exclusivo para assinantes",
    r"assine para ler",
    r"conte[úu]do exclusivo",
    r"fa[çc]a login para",
    # Italian
    r"riservato agli abbonati",
    r"abbonati per leggere",
    r"contenuto riservato",
    # German
    r"exklusiv f[üu]r abonnenten",
    r"jetzt abonnieren",
    r"weiterlesen mit",
    r"premium-inhalt",
]

_PAYWALL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PAYWALL_PHRASES]

# ── CSS class/id patterns (broad) ────────────────────────────
_CSS_PAYWALL_PATTERNS = [
    re.compile(r"paywall", re.IGNORECASE),
    re.compile(r"premium.?wall", re.IGNORECASE),
    re.compile(r"subscribe.?wall", re.IGNORECASE),
    re.compile(r"regwall", re.IGNORECASE),
    re.compile(r"metered", re.IGNORECASE),
    re.compile(r"locked.?content", re.IGNORECASE),
    re.compile(r"gate(?:d|keeper)", re.IGNORECASE),
    re.compile(r"truncat", re.IGNORECASE),
]

# Minimum body length (chars) for a "full" article
_MIN_BODY_LENGTH = 500


class PaywallDetector:
    """Detects paywall/truncated content using heuristics."""

    def detect(self, body: str, raw_html: str | None = None) -> tuple[bool, list[str]]:
        """
        Analyze article body (and optionally raw HTML) for paywall signals.

        Returns:
            (is_truncated, indicators) where indicators lists which heuristics fired.
        """
        indicators: list[str] = []

        # 1. Short body
        if len(body.strip()) < _MIN_BODY_LENGTH:
            indicators.append(f"body_too_short ({len(body.strip())} chars)")

        # 2. Keyword scan in body text
        for pattern in _PAYWALL_PATTERNS:
            if pattern.search(body):
                indicators.append(f"keyword: {pattern.pattern}")
                break  # one keyword is enough

        # 3. Abrupt ending — body doesn't end with sentence-ending punctuation
        stripped = body.rstrip()
        if stripped and stripped[-1] not in '.?!"\u201d\u00bb':
            # Only flag if body is also suspiciously short for a full article
            if len(stripped) < 2000:
                indicators.append("abrupt_ending")

        # 4. HTML-based detection (if raw HTML is provided)
        if raw_html:
            indicators.extend(self._scan_html(raw_html))

        is_truncated = len(indicators) > 0

        if is_truncated:
            logger.info("Paywall/truncation detected", indicators=indicators, body_len=len(body))

        return is_truncated, indicators

    def _scan_html(self, html: str) -> list[str]:
        """Scan raw HTML for paywall-related CSS classes, ids, and data attributes."""
        indicators = []
        try:
            soup = BeautifulSoup(html, "lxml")

            # Check class/id attributes for paywall patterns
            for tag in soup.find_all(True, limit=500):
                attrs_to_check = []
                for attr in ("class", "id", "data-testid", "data-component"):
                    val = tag.get(attr)
                    if val:
                        if isinstance(val, list):
                            attrs_to_check.extend(val)
                        else:
                            attrs_to_check.append(str(val))

                for attr_val in attrs_to_check:
                    for pattern in _CSS_PAYWALL_PATTERNS:
                        if pattern.search(attr_val):
                            indicators.append(f"html_element: {pattern.pattern} in '{attr_val}'")
                            return indicators  # one HTML hit is enough

            # Check for data-paywall or similar data attributes
            for tag in soup.find_all(attrs={"data-paywall": True}):
                indicators.append("html_data_attr: data-paywall")
                return indicators

        except Exception as e:
            logger.warning("HTML paywall scan failed", error=str(e))

        return indicators
