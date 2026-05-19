"""Rebuild FAISS indexes for all or a specific knowledge base."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import settings
from app.core.loader import load_document
from app.core.splitter import split_documents
from app.core.vector_store import vector_store_manager
from app.models.database import async_session_factory, engine, Base
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from sqlalchemy import select


async def rebuild(kb_id: int | None = None):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        if kb_id:
            kbs = [await db.get(KnowledgeBase, kb_id)]
            kbs = [kb for kb in kbs if kb]
        else:
            result = await db.execute(select(KnowledgeBase))
            kbs = list(result.scalars().all())

        for kb in kbs:
            print(f"\n=== Rebuilding index for KB #{kb.id}: {kb.name} ===")
            result = await db.execute(
                select(Document).where(Document.knowledge_base_id == kb.id, Document.status == "ready")
            )
            docs = result.scalars().all()

            all_chunks = []
            for doc in docs:
                try:
                    raw = load_document(doc.file_path)
                    chunks = split_documents(raw)
                    for chunk in chunks:
                        chunk.metadata["document_id"] = doc.id
                        chunk.metadata["knowledge_base_id"] = kb.id
                    all_chunks.extend(chunks)
                    print(f"  ✓ {doc.filename}: {len(chunks)} chunks")
                except Exception as exc:
                    print(f"  ✗ {doc.filename}: {exc}")

            vector_store_manager.rebuild_index(kb.id, all_chunks)
            print(f"  Total: {len(all_chunks)} chunks indexed")

    print("\nDone.")


if __name__ == "__main__":
    target_kb_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(rebuild(target_kb_id))
