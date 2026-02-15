"""Available news sources configuration."""

from app.schemas import AvailableSource

AVAILABLE_SOURCES: list[AvailableSource] = [
    # ── Spanish Media ─────────────────────────────────────────
    AvailableSource(name="El País", slug="elpais", country="ES", type="rss"),
    AvailableSource(name="El Mundo", slug="elmundo", country="ES", type="rss"),
    AvailableSource(name="ABC", slug="abc", country="ES", type="rss"),
    AvailableSource(name="La Vanguardia", slug="lavanguardia", country="ES", type="rss"),
    AvailableSource(name="20 Minutos", slug="20minutos", country="ES", type="rss"),
    AvailableSource(name="elDiario.es", slug="eldiario", country="ES", type="rss"),
    AvailableSource(name="Público", slug="publico", country="ES", type="rss"),
    AvailableSource(name="La Razón", slug="larazon", country="ES", type="rss"),
    AvailableSource(name="RTVE", slug="rtve", country="ES", type="rss"),
    AvailableSource(name="Cadena SER", slug="cadenaser", country="ES", type="rss"),
]

# RSS Feed URLs indexed by slug
SOURCE_RSS_FEEDS: dict[str, list[str]] = {
    "elpais": [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    ],
    "elmundo": [
        "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    ],
    "abc": [
        "https://www.abc.es/rss/2.0/portada/",
    ],
    "lavanguardia": [
        "https://www.lavanguardia.com/rss/home.xml",
    ],
    "20minutos": [
        "https://www.20minutos.es/rss/",
    ],
    "eldiario": [
        "https://www.eldiario.es/rss/",
    ],
    "publico": [
        "https://www.publico.es/rss/",
    ],
    "larazon": [
        "https://www.larazon.es/rss/portada.xml",
    ],
    "rtve": [
        "https://www.rtve.es/api/noticias.rss",
    ],
    "cadenaser": [
        "https://cadenaser.com/rss/",
    ],
}
