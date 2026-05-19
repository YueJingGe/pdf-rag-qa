"""Knowledge base management API routes."""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.core.vector_store import vector_store_manager

router = APIRouter(prefix="/api/knowledge_bases", tags=["knowledge_bases"])


class KBCreateRequest(BaseModel):
    name: str
    description: str = ""
    permission: str = "private"


class KBResponse(BaseModel):
    id: int
    name: str
    description: str
    permission: str
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=KBResponse)
async def create_knowledge_base(req: KBCreateRequest, db: AsyncSession = Depends(get_db)):
    kb = KnowledgeBase(name=req.name, description=req.description, permission=req.permission)
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return KBResponse(
        id=kb.id, name=kb.name, description=kb.description,
        permission=kb.permission, document_count=0,
        created_at=kb.created_at, updated_at=kb.updated_at,
    )


@router.get("", response_model=list[KBResponse])
async def list_knowledge_bases(db: AsyncSession = Depends(get_db)):
    from app.models.document import Document
    from sqlalchemy import func
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    kbs = result.scalars().all()
    responses = []
    for kb in kbs:
        count_result = await db.execute(
            select(func.count(Document.id)).where(
                Document.knowledge_base_id == kb.id,
                Document.status == "ready",
            )
        )
        ready_count = count_result.scalar() or 0
        responses.append(KBResponse(
            id=kb.id, name=kb.name, description=kb.description,
            permission=kb.permission, document_count=ready_count,
            created_at=kb.created_at, updated_at=kb.updated_at,
        ))
    return responses


@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(kb_id: int, db: AsyncSession = Depends(get_db)):
    from app.models.document import Document
    from sqlalchemy import func
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    count_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.knowledge_base_id == kb.id,
            Document.status == "ready",
        )
    )
    ready_count = count_result.scalar() or 0
    return KBResponse(
        id=kb.id, name=kb.name, description=kb.description,
        permission=kb.permission, document_count=ready_count,
        created_at=kb.created_at, updated_at=kb.updated_at,
    )


class KBUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


# 更新名称/描述
@router.put("/{kb_id}", response_model=KBResponse)
async def update_knowledge_base(kb_id: int, req: KBUpdateRequest, db: AsyncSession = Depends(get_db)):
    from app.models.document import Document
    from sqlalchemy import func

    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    if req.name is not None:
        kb.name = req.name
    if req.description is not None:
        kb.description = req.description

    await db.commit()
    await db.refresh(kb)

    count_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.knowledge_base_id == kb.id,
            Document.status == "ready",
        )
    )
    ready_count = count_result.scalar() or 0
    return KBResponse(
        id=kb.id, name=kb.name, description=kb.description,
        permission=kb.permission, document_count=ready_count,
        created_at=kb.created_at, updated_at=kb.updated_at,
    )


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: int, db: AsyncSession = Depends(get_db)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    vector_store_manager.delete_index(kb_id)
    await db.delete(kb)
    await db.commit()
    return {"detail": "Knowledge base deleted"}
