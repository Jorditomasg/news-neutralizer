---
name: news-analysis
description: Build news scraping, NLP analysis, bias detection, and neutralization pipelines. Use when implementing article extraction, topic clustering, sentiment analysis, LLM-based bias detection, or generating neutralized summaries.
---

# News Analysis & Neutralization Pipeline

Build intelligent pipelines for scraping, analyzing, and neutralizing news articles.

## Pipeline Architecture

```
Input (URL or topic) → Extraction → Clustering → Analysis → Neutralization → Output
```

### 1. Article Extraction
```python
import httpx
from bs4 import BeautifulSoup

class ArticleExtractor:
    """Extract clean article content from URLs."""

    async def extract(self, url: str) -> ExtractedArticle:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._get_headers())
        soup = BeautifulSoup(resp.text, "html.parser")
        return ExtractedArticle(
            title=self._extract_title(soup),
            body=self._extract_body(soup),
            author=self._extract_author(soup),
            published_at=self._extract_date(soup),
            source_url=url,
        )
```

### 2. Multi-Source Search
```python
class NewsSearchService:
    """Search multiple source types in parallel."""

    async def search(self, query: str, sources: list[str]) -> list[RawArticle]:
        tasks = []
        for source in sources:
            scraper = ScraperFactory.get(source)
            tasks.append(scraper.search(query))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._flatten_valid(results)
```

### 3. Topic Clustering
```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

class TopicClusterer:
    """Group articles by topic similarity using embeddings."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)

    def cluster(self, articles: list[Article], threshold: float = 0.3) -> list[Cluster]:
        texts = [f"{a.title} {a.body[:500]}" for a in articles]
        embeddings = self.model.encode(texts)
        clustering = AgglomerativeClustering(
            n_clusters=None, distance_threshold=threshold, metric="cosine"
        )
        labels = clustering.fit_predict(embeddings)
        return self._group_by_label(articles, labels)
```

### 4. LLM-Based Bias Analysis

#### Structured Prompt Pattern
```python
ANALYSIS_PROMPT = """Eres un analista de medios experto en detectar sesgo informativo.

Analiza los siguientes artículos sobre el mismo tema y genera un informe estructurado.

ARTÍCULOS:
{articles_text}

Genera un JSON con esta estructura exacta:
{{
  "topic_summary": "Resumen del tema en 1-2 frases",
  "objective_facts": [
    "Hecho verificable 1",
    "Hecho verificable 2"
  ],
  "bias_elements": [
    {{
      "source": "nombre del medio",
      "type": "sensacionalismo|omisión|framing|adjetivación|falacia",
      "original_text": "texto original del artículo",
      "explanation": "por qué es sesgo y no información factual",
      "severity": 1-5
    }}
  ],
  "neutralized_summary": "Resumen basado exclusivamente en hechos verificables",
  "source_bias_scores": {{
    "nombre_medio": {{
      "score": 0.0-1.0,
      "direction": "izquierda|centro|derecha|sensacionalista",
      "confidence": 0.0-1.0
    }}
  }}
}}
"""
```

### 5. AI Provider Abstraction (Strategy Pattern)

```python
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def validate_key(self, key: str) -> bool: ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float: ...

class AIProviderFactory:
    _providers: dict[str, type[AIProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[AIProvider]):
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str, api_key: str) -> AIProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        return cls._providers[name](api_key=api_key)
```

## Scraping Best Practices

- **Respect `robots.txt`**: Always check before scraping
- **Rate limiting**: Minimum 1-2 seconds between requests per domain
- **User-Agent rotation**: Rotate realistic browser user-agents
- **RSS first**: Prefer RSS/Atom feeds over HTML scraping
- **Error resilience**: Retry with exponential backoff; skip failing sources
- **Content validation**: Verify extracted text is actual article content, not boilerplate

## Spanish News Sources Configuration

| Source | Type | URL Pattern |
|--------|------|-------------|
| El País | RSS | `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada` |
| El Mundo | RSS | `https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml` |
| La Vanguardia | RSS | `https://www.lavanguardia.com/rss/home.xml` |
| ABC | RSS | `https://www.abc.es/rss/2.0/portada/` |
| elDiario.es | RSS | `https://www.eldiario.es/rss/` |
| 20 Minutos | RSS | `https://www.20minutos.es/rss/` |

## Bias Detection Categories

1. **Sensacionalismo**: Titulares exagerados, lenguaje alarmista
2. **Omisión**: Datos relevantes intencionalmente excluidos
3. **Framing**: Encuadre que predispone la interpretación
4. **Adjetivación cargada**: Adjetivos valorativos vs. descriptivos
5. **Falacia**: Argumentos lógicamente incorrectos presentados como hechos
6. **Cherry-picking**: Selección parcial de datos que distorsiona
