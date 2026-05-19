"""FAISS vector store manager with multi-knowledge-base isolation."""

from __future__ import annotations

from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.core.embeddings import get_embedding_model


class VectorStoreManager:
    """Manage per-knowledge-base FAISS indexes."""

    def __init__(self):
        self._cache: dict[int, FAISS] = {}
        self._embedding_model: Embeddings | None = None

    @property
    def embedding_model(self) -> Embeddings:
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def _index_dir(self, knowledge_base_id: int) -> Path:
        return settings.faiss_index_dir / str(knowledge_base_id)

    def get_store(self, knowledge_base_id: int) -> FAISS | None:
        """Load a FAISS index from cache or disk."""
        if knowledge_base_id in self._cache:
            return self._cache[knowledge_base_id]

        index_path = self._index_dir(knowledge_base_id)
        if not index_path.exists():
            return None

        store = FAISS.load_local(
            str(index_path),
            self.embedding_model,
            allow_dangerous_deserialization=True,
        )
        self._cache[knowledge_base_id] = store
        return store

    def add_documents(self, knowledge_base_id: int, documents: list[Document]) -> int:
        """Add documents to a knowledge base's FAISS index."""
        if not documents:
            return 0

        store = self.get_store(knowledge_base_id)
        if store is None:
            store = FAISS.from_documents(documents, self.embedding_model)
        else:
            store.add_documents(documents)

        self._cache[knowledge_base_id] = store
        self._save(knowledge_base_id, store)
        return len(documents)

    def delete_index(self, knowledge_base_id: int):
        """Delete the entire FAISS index for a knowledge base."""
        import shutil

        self._cache.pop(knowledge_base_id, None)
        index_path = self._index_dir(knowledge_base_id)
        if index_path.exists():
            shutil.rmtree(index_path)

    def rebuild_index(self, knowledge_base_id: int, documents: list[Document]):
        """Rebuild the entire FAISS index from scratch."""
        self.delete_index(knowledge_base_id)
        if documents:
            self.add_documents(knowledge_base_id, documents)

    def _save(self, knowledge_base_id: int, store: FAISS):
        index_path = self._index_dir(knowledge_base_id)
        index_path.mkdir(parents=True, exist_ok=True)
        store.save_local(str(index_path))


vector_store_manager = VectorStoreManager()
