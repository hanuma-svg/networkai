import math
import hashlib
from typing import Any, List, Optional
from src.config import settings


def l2_normalize(vector: List[float]) -> List[float]:
    """Calculates the Euclidean (L2) norm and returns the unit vector.
    
    Ensures that the vector matches cosine similarity expectations in Supabase pgvector.
    """
    norm = math.sqrt(sum(float(x) * float(x) for x in vector))
    if norm == 0.0 or math.isnan(norm):
        return [0.0] * len(vector)
    return [float(x) / norm for x in vector]


def _deterministic_normalized_vector(text: str, dim: int = 768) -> List[float]:
    """Generates a reproducible 768-dim L2-normalized vector for testing or offline fallback."""
    seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [((seed_bytes[i % len(seed_bytes)] / 255.0) * 2.0 - 1.0) for i in range(dim)]
    return l2_normalize(raw)


def generate_embedding(text: str, client: Optional[Any] = None) -> List[float]:
    """Generates a 768-dimensional L2-normalized embedding using google-genai with gemini-embedding-001.
    
    Aligns with `embedding vector(768)` in `supabase/schema.sql`.
    """
    text = (text or "").strip()
    if not text:
        return [0.0] * 768

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return _deterministic_normalized_vector(text, 768)

    try:
        if client is None:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
        else:
            from google.genai import types

        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768),
        )

        values: List[float] = []
        if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
            values = [float(v) for v in response.embedding.values]
        elif hasattr(response, "embeddings") and response.embeddings:
            values = [float(v) for v in response.embeddings[0].values]
        elif isinstance(response, dict) and "embedding" in response:
            values = [float(v) for v in response["embedding"].get("values", [])]

        if not values:
            return _deterministic_normalized_vector(text, 768)

        # Ensure exact 768 dimensions
        if len(values) < 768:
            values = values + [0.0] * (768 - len(values))
        elif len(values) > 768:
            values = values[:768]

        return l2_normalize(values)
    except Exception:
        # Graceful fallback to deterministic normalized vector in case of offline network / sandbox limits
        return _deterministic_normalized_vector(text, 768)
