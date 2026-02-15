"""Article content extractor — extracts clean text from news URLs."""

from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


@dataclass
class ExtractedArticle:
    """Extracted article data."""

    title: str
    body: str
    source_name: str
    source_url: str
    author: str | None = None
    published_at: datetime | None = None
    topics: list[str] = field(default_factory=list)


class ArticleExtractor:
    """Extract clean article content from URLs using httpx + BeautifulSoup."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    async def extract(self, url: str) -> ExtractedArticle:
        """Fetch a URL and extract the article content."""
        logger.info("Extracting article", url=url)

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": self.USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        return ExtractedArticle(
            title=self._extract_title(soup),
            body=self._extract_body(soup),
            source_name=self._extract_source_name(url),
            source_url=url,
            author=self._extract_author(soup),
            published_at=self._extract_date(soup),
            topics=self._extract_topics(soup),
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title from common patterns."""
        # Try Open Graph title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return str(og_title["content"]).strip()

        # Then <h1>
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Fallback to <title>
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else "Sin título"

    def _extract_body(self, soup: BeautifulSoup) -> str:
        """Extract article body text from common patterns."""
        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        # Try common article selectors
        selectors = [
            "article",
            '[itemprop="articleBody"]',
            ".article-body",
            ".story-body",
            ".entry-content",
            ".post-content",
            "#article-body",
            "main",
        ]

        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                paragraphs = container.find_all("p")
                if paragraphs:
                    text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                    if len(text) > 100:
                        return text

        # Fallback: all <p> tags
        paragraphs = soup.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
        return text if text else "No se pudo extraer el contenido del artículo."

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        """Extract author from meta tags or common patterns."""
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return str(meta_author["content"]).strip()

        author_tag = soup.find(attrs={"class": lambda c: c and "author" in str(c).lower()})
        if author_tag:
            return author_tag.get_text(strip=True)

        return None

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        """Extract publication date from meta tags."""
        for prop in ["article:published_time", "datePublished", "og:article:published_time"]:
            meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if meta and meta.get("content"):
                try:
                    return datetime.fromisoformat(str(meta["content"]).replace("Z", "+00:00"))
                except ValueError:
                    continue

        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            try:
                return datetime.fromisoformat(str(time_tag["datetime"]).replace("Z", "+00:00"))
            except ValueError:
                pass

        return None

    def _extract_source_name(self, url: str) -> str:
        """Derive source name from URL domain."""
        domain = urlparse(url).netloc
        # Clean up common prefixes
        for prefix in ["www.", "m.", "mobile."]:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        # Remove TLD for cleaner name
        return domain.split(".")[0].capitalize()

    def _extract_topics(self, soup: BeautifulSoup) -> list[str]:
        """Extract topics/keywords from meta tags."""
        topics = []

        # Keywords meta tag
        keywords_meta = soup.find("meta", attrs={"name": "keywords"})
        if keywords_meta and keywords_meta.get("content"):
            raw = str(keywords_meta["content"])
            topics.extend(k.strip() for k in raw.split(",") if k.strip())

        # Article tags
        article_tags = soup.find("meta", property="article:tag")
        if article_tags and article_tags.get("content"):
            topics.append(str(article_tags["content"]).strip())

        # Limit and deduplicate
        seen = set()
        unique_topics = []
        for topic in topics[:10]:
            lower = topic.lower()
            if lower not in seen:
                seen.add(lower)
                unique_topics.append(topic)

        return unique_topics
