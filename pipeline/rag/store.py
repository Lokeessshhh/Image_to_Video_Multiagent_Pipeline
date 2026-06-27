import os
import chromadb
from chromadb.api.types import Documents, Embeddings
from pipeline.rag.seed_data import STYLE_GUIDES, REMOTION_API_SNIPPETS

class LocalKeywordEmbeddingFunction(chromadb.EmbeddingFunction[Documents]):
    """
    A lightweight, deterministic keyword-based embedding function.
    Guarantees 100% offline functionality (no Hugging Face model downloads),
    extremely low latency, and zero dependency on external network calls.
    """
    def __init__(self):
        # High-relevance keywords for our styles and Remotion APIs
        self.vocabulary = [
            "cinematic", "slow", "emotional", "warm", "crossfade", "zoom", "fade", "panning",
            "upbeat", "fast", "cuts", "bold", "uppercase", "energetic", "bounce", "spring",
            "corporate", "professional", "clean", "minimal", "slide", "pacing", "caption",
            "sequence", "interpolate", "staticfile", "absolutefill", "transition", "error", "compile"
        ]

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            text_lower = text.lower()
            vector = [0.0] * len(self.vocabulary)
            for idx, word in enumerate(self.vocabulary):
                if word in text_lower:
                    # Give extra weight to exact keyword matches
                    vector[idx] = 1.0
            
            # Simple L2 normalization
            squared_sum = sum(v ** 2 for v in vector)
            if squared_sum > 0:
                magnitude = squared_sum ** 0.5
                vector = [v / magnitude for v in vector]
            else:
                # Fallback to dummy small values
                vector = [0.01] * len(self.vocabulary)
            embeddings.append(vector)
        return embeddings

    @staticmethod
    def name() -> str:
        return "LocalKeywordEmbeddingFunction"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "LocalKeywordEmbeddingFunction":
        return LocalKeywordEmbeddingFunction()

class RagStore:
    def __init__(self, db_path="pipeline/rag/chroma_db"):
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedding_fn = LocalKeywordEmbeddingFunction()
        
        # Get or create collections
        self.styles_col = self.client.get_or_create_collection(
            name="style_guides",
            embedding_function=self.embedding_fn
        )
        self.api_col = self.client.get_or_create_collection(
            name="remotion_api",
            embedding_function=self.embedding_fn
        )
        
        # Seed if empty
        self._seed_if_empty()

    def _seed_if_empty(self):
        # Seed Style Guides
        if self.styles_col.count() == 0:
            print("Seeding style guides collection...")
            ids = [item["id"] for item in STYLE_GUIDES]
            documents = [item["content"] for item in STYLE_GUIDES]
            metadatas = [{"theme": item["theme"]} for item in STYLE_GUIDES]
            self.styles_col.add(ids=ids, documents=documents, metadatas=metadatas)

        # Seed Remotion API Snippets
        if self.api_col.count() == 0:
            print("Seeding Remotion API snippets collection...")
            ids = [item["id"] for item in REMOTION_API_SNIPPETS]
            documents = [item["content"] for item in REMOTION_API_SNIPPETS]
            metadatas = [{"component": item["component"]} for item in REMOTION_API_SNIPPETS]
            self.api_col.add(ids=ids, documents=documents, metadatas=metadatas)

    def retrieve_style(self, query: str, n_results: int = 1) -> str:
        results = self.styles_col.query(
            query_texts=[query],
            n_results=min(n_results, self.styles_col.count())
        )
        if results and results["documents"] and results["documents"][0]:
            return "\n\n".join(results["documents"][0])
        return ""

    def retrieve_api(self, query: str, n_results: int = 2) -> str:
        results = self.api_col.query(
            query_texts=[query],
            n_results=min(n_results, self.api_col.count())
        )
        if results and results["documents"] and results["documents"][0]:
            return "\n\n".join(results["documents"][0])
        return ""
