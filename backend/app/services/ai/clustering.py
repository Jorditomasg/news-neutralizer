import numpy as np
from typing import List, Optional
import structlog
from app.services.scraper.search_federated import ArticleHit

# scikit-learn
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

# Sentence Transformers for local high-speed embeddings
try:
    from sentence_transformers import SentenceTransformer
    # all-MiniLM-L6-v2 is extremely fast, very small (80MB), and good enough for news clustering
    _embedder = SentenceTransformer('all-MiniLM-L6-v2')
    HAS_EMBEDDER = True
except ImportError:
    _embedder = None
    HAS_EMBEDDER = False

logger = structlog.get_logger(__name__)


class SemanticClusterer:
    """
    Groups raw search hits into dense semantic clusters to ensure the AI 
    only analyzes articles about the exact same event.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        if not HAS_EMBEDDER:
            logger.warning("sentence-transformers not installed, skipping embeddings")
            return np.zeros((len(texts), 384)) # Dummy fallback
            
        logger.debug("Generating embeddings", count=len(texts))
        
        # sentence-transformers encodes returning a numpy array ready for sklearn
        embeddings = _embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings

    def filter_by_reference_query(self, hits: List[ArticleHit], reference_text: str) -> List[ArticleHit]:
        """
        Calculates cosine similarity of each hit against a reference text (like a source URL).
        Discards any hit below the strict threshold.
        """
        if not hits or not HAS_EMBEDDER:
            return hits
            
        texts = [f"{hit.title} {hit.snippet or ''}" for hit in hits]
        # Get query embedding (1, D)
        query_emb = self._get_embeddings([reference_text])
        # Get hits embeddings (N, D)
        hits_embs = self._get_embeddings(texts)
        
        # Calculate cosine similarites (1, N)
        similarities = cosine_similarity(query_emb, hits_embs)[0]
        
        filtered = []
        for i, score in enumerate(similarities):
            # Log the scores for debugging
            logger.debug("Hit similarity", title=hits[i].title[:40], score=score)
            if score >= self.similarity_threshold:
                filtered.append(hits[i])
                
        logger.info("Semantic filtering complete (by reference)", 
                    original_count=len(hits), 
                    filtered_count=len(filtered),
                    threshold=self.similarity_threshold)
        return filtered

    def get_densest_cluster(self, hits: List[ArticleHit]) -> List[ArticleHit]:
        """
        Uses DBSCAN on the embeddings to find the most dense group of articles.
        Useful when the user typed a manual query and we don't have a single source URL.
        """
        if not hits or len(hits) < 3 or not HAS_EMBEDDER:
            # Not enough data or no embedder, return top 10 as fallback
            return hits[:10]
            
        texts = [f"{hit.title} {hit.snippet or ''}" for hit in hits]
        embs = self._get_embeddings(texts)
        
        # DBSCAN parameters:
        # eps is the max distance between two samples. 
        # Since we use normalized embeddings, Euclidean distance squared is 2*(1-cosine_sim).
        # We want cosine_sim > 0.85 roughly.
        # So distance = sqrt(2 * (1 - 0.85)) = sqrt(0.3) ~ 0.54. Let's use 0.5.
        min_samples = max(2, min(4, len(hits) // 4)) # Minimum cluster size
        
        dbscan = DBSCAN(eps=0.5, min_samples=min_samples, metric='euclidean')
        labels = dbscan.fit_predict(embs)
        
        # Find the label with the most items (excluding -1 noise)
        from collections import Counter
        counts = Counter(labels)
        if -1 in counts:
            del counts[-1]
            
        if not counts:
            logger.warning("No semantic cluster found via DBSCAN, falling back to top hits")
            return hits[:5] # Fallback
            
        best_cluster_label = counts.most_common(1)[0][0]
        cluster_hits = [hits[i] for i, label in enumerate(labels) if label == best_cluster_label]
        
        logger.info("Semantic DBSCAN complete", 
                    total_hits=len(hits), 
                    cluster_size=len(cluster_hits), 
                    noise_eliminated=len(hits) - len(cluster_hits))
                    
        return cluster_hits
