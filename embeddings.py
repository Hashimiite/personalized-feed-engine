"""Text embeddings behind LangChain's Embeddings interface.

The default runs BAAI/bge-small-en-v1.5 locally through FastEmbed (ONNX, CPU only, no API key).
Set EMBEDDINGS=fake to use LangChain's deterministic fake embeddings, which tests use for speed.
"""

import os
from functools import lru_cache

from fastembed import TextEmbedding
from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings

DIM = 384
MODEL = "BAAI/bge-small-en-v1.5"


class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str = MODEL):
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache
def get_embeddings() -> Embeddings:
    if os.getenv("EMBEDDINGS") == "fake":
        return DeterministicFakeEmbedding(size=DIM)
    return FastEmbedEmbeddings()


def post_text(topic: str, content: str) -> str:
    """The text that represents a post in vector space."""
    return f"{topic}: {content}"
