"""Chat API with SSE streaming support."""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.models.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.conversation import Conversation, Message
from app.core.rag_chain import rag_stream, rag_query, plain_chat_stream

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    knowledge_base_id: int | None = None
    question: str
    conversation_id: int | None = None
    use_hyde: bool = False


class ConversationResponse(BaseModel):
    id: int
    knowledge_base_id: int
    title: str

    model_config = {"from_attributes": True}


@router.post("/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Determine if this is a plain chat (no KB) or RAG chat
    is_plain_chat = req.knowledge_base_id is None or req.knowledge_base_id == 0

    if not is_plain_chat:
        kb = await db.get(KnowledgeBase, req.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

    if req.conversation_id:
        conversation = await db.get(Conversation, req.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            knowledge_base_id=req.knowledge_base_id or 0,
            title=req.question[:50],
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    history_msgs = list(reversed(result.scalars().all()))
    chat_history = [{"role": m.role, "content": m.content} for m in history_msgs]

    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    await db.commit()

    async def event_generator():
        full_answer = ""
        citations = []

        yield {"event": "conversation", "data": json.dumps({
            "conversation_id": conversation.id,
        })}

        if is_plain_chat:
            # Plain chat mode: call LLM directly without RAG 直接调用 LLM 不走 RAG 检索链
            async for chunk in plain_chat_stream(req.question, chat_history):
                if chunk["type"] == "token":
                    full_answer += chunk["content"]
                    yield {"event": "token", "data": json.dumps({"content": chunk["content"]})}
                elif chunk["type"] == "done":
                    yield {"event": "done", "data": json.dumps({"content": full_answer})}
        else:
            async for chunk in rag_stream(
                req.knowledge_base_id, req.question, chat_history, use_hyde=req.use_hyde
            ):
                if chunk["type"] == "token":
                    full_answer += chunk["content"]
                    yield {"event": "token", "data": json.dumps({"content": chunk["content"]})}
                elif chunk["type"] == "citations":
                    citations = chunk["content"]
                    yield {"event": "citations", "data": json.dumps({"citations": citations})}
                elif chunk["type"] == "retrieval_debug":
                    yield {"event": "retrieval_debug", "data": json.dumps(chunk["content"])}
                elif chunk["type"] == "done":
                    yield {"event": "done", "data": json.dumps({"content": full_answer})}

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_answer,
            citations=citations,
        )
        db.add(assistant_msg)
        await db.commit()

    return EventSourceResponse(event_generator())


@router.post("/query")
async def chat_query(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Non-streaming RAG query for A/B testing."""
    kb = await db.get(KnowledgeBase, req.knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    chat_history: list[dict] = []
    if req.conversation_id:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == req.conversation_id)
            .order_by(Message.created_at.desc())
            .limit(10) # 每次请求从数据库加载最近 10 条消息
        )
        history_msgs = list(reversed(result.scalars().all()))
        chat_history = [{"role": m.role, "content": m.content} for m in history_msgs]

    try:
        response = await rag_query(
            req.knowledge_base_id, req.question, chat_history, use_hyde=req.use_hyde
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(exc)}")


@router.get("/conversations/{kb_id}", response_model=list[ConversationResponse])
async def list_conversations(kb_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.knowledge_base_id == kb_id)
        .order_by(Conversation.created_at.desc())
    )
    return result.scalars().all()


@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": m.citations,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.execute(sa_delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()
    return {"detail": "Conversation deleted"}
