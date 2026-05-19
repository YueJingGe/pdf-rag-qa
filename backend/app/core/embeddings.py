"""Embedding model factory. Provider configured via EMBEDDING_PROVIDER in .env"""

import os
from langchain_core.embeddings import Embeddings
from app.core.config import settings

# Set HuggingFace mirror for China network (read from .env)
_hf_endpoint = os.environ.get("HF_ENDPOINT", "")
if not _hf_endpoint:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    os.environ["HF_HUB_URL"] = "https://hf-mirror.com"


def get_embedding_model() -> Embeddings:
    """Return the configured embedding model instance.

    Reads EMBEDDING_PROVIDER from .env:
      - "huggingface": uses local BAAI/bge-small-zh-v1.5 (free, no API key)
      - "dashscope": uses Aliyun text-embedding-v3 (requires DASHSCOPE_API_KEY)
    """
    if settings.embedding_provider == "dashscope":
        if not settings.dashscope_api_key:
            raise ValueError(
                "EMBEDDING_PROVIDER=dashscope but DASHSCOPE_API_KEY is empty. "
                "Please set it in .env or switch to EMBEDDING_PROVIDER=huggingface"
            )
        from langchain_community.embeddings import DashScopeEmbeddings
        return DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=settings.dashscope_api_key,
        )

    # Default: HuggingFace local model (free, no API key needed)
    from langchain_community.embeddings import HuggingFaceBgeEmbeddings
    return HuggingFaceBgeEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
