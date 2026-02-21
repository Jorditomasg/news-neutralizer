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

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Helper to generate generic embeddings."""
    if not HAS_EMBEDDER or not texts:
        return [[] for _ in texts]
    embeddings = _embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


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

    def filter_by_reference_query(self, hits: List[ArticleHit], reference_text: str, threshold: float | None = None) -> List[ArticleHit]:
        """
        Calculates cosine similarity of each hit against a reference text (like a source URL).
        Discards any hit below the given threshold (defaults to self.similarity_threshold).
        """
        if not hits or not HAS_EMBEDDER:
            return hits
            
        _threshold = threshold if threshold is not None else self.similarity_threshold
            
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
            if score >= _threshold:
                filtered.append(hits[i])
                
        logger.info("Semantic filtering complete (by reference)", 
                    original_count=len(hits), 
                    filtered_count=len(filtered),
                    threshold=_threshold)
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
        # We want cosine_sim > 0.87 roughly.
        # So distance = sqrt(2 * (1 - 0.87)) = sqrt(0.26) ~ 0.51. Let's use 0.45 for tighter clusters.
        min_samples = max(2, min(4, len(hits) // 4)) # Minimum cluster size
        
        dbscan = DBSCAN(eps=0.45, min_samples=min_samples, metric='euclidean')
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
        cluster_indices = [i for i, label in enumerate(labels) if label == best_cluster_label]
        
        # Sort cluster members by similarity to the cluster centroid
        cluster_embs = embs[cluster_indices]
        centroid = cluster_embs.mean(axis=0, keepdims=True)
        sims = cosine_similarity(centroid, cluster_embs)[0]
        sorted_indices = np.argsort(-sims)  # Descending
        cluster_hits = [hits[cluster_indices[i]] for i in sorted_indices]
        
        logger.info("Semantic DBSCAN complete", 
                    total_hits=len(hits), 
                    cluster_size=len(cluster_hits), 
                    noise_eliminated=len(hits) - len(cluster_hits))
                    
        return cluster_hits

class FactAssociator:
    """Groups facts from multiple articles into consensus points."""
    
    def group_facts(self, facts: List['StructuredFact'], eps: float = 0.5) -> List[List['StructuredFact']]:
        """
        Groups facts based on their vector embeddings using DBSCAN.
        Returns a list of fact clusters.
        """
        if not facts:
            return []
            
        embs = [f.embedding for f in facts]
        # Check if embeddings are present, fallback to generation if not
        if None in embs:
            logger.warning("Missing embeddings in StructuredFacts, regenerating fallback embeddings")
            texts = [f.content for f in facts]
            embs = generate_embeddings(texts)
            
        embs_array = np.array(embs)
        
        # min_samples=1 so unique facts aren't dropped as noise (-1)
        dbscan = DBSCAN(eps=eps, min_samples=1, metric='euclidean')
        labels = dbscan.fit_predict(embs_array)
        
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(facts[idx])
            
        logger.info("Fact association complete", 
                    total_facts=len(facts), 
                    num_clusters=len(clusters))
                    
        return list(clusters.values())
