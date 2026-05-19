"""Advanced retrieval strategies: HyDE and hybrid search."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.vector_store import vector_store_manager


HYDE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "请根据用户问题，生成一段可能包含答案的假想文档段落（中文），用于辅助检索。"),
    ("human", "{question}"),
])


def _get_llm() -> ChatOpenAI:
    if not settings.deepseek_api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY is not configured. "
            "Please set it in backend/.env file."
        )
    return ChatOpenAI(
        model=settings.deepseek_model,
        openai_api_key=settings.deepseek_api_key,
        openai_api_base=settings.deepseek_base_url,
        temperature=0.0,
        max_tokens=256,
    )


async def hyde_retrieve(
    knowledge_base_id: int,
    question: str,
    top_k: int | None = None,
) -> list[Document]:
    """HyDE: generate a hypothetical document, then retrieve with it."""
    top_k = top_k or settings.retrieval_top_k
    store = vector_store_manager.get_store(knowledge_base_id)
    if store is None:
        return []

    llm = _get_llm()
    chain = HYDE_PROMPT | llm
    hypothetical_doc = await chain.ainvoke({"question": question})

    results = store.similarity_search(hypothetical_doc.content, k=top_k)
    return results


def _chinese_tokenize(text: str) -> list[str]:
    """Simple character n-gram + word tokenizer for Chinese text.

    Uses regex to split into Chinese character sequences, numbers, and latin words,
    then generates unigrams and bigrams for better BM25 matching.
    """
    import re
    # Extract meaningful tokens: Chinese chars, numbers, latin words
    raw_tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', text.lower())
    tokens = []
    for token in raw_tokens:
        if len(token) <= 1:
            tokens.append(token)
        elif all('\u4e00' <= c <= '\u9fff' for c in token):
            # Chinese: generate character bigrams + full token
            tokens.append(token)
            for i in range(len(token) - 1):
                tokens.append(token[i:i+2])
        else:
            tokens.append(token)
    return tokens


def bm25_retrieve(
    corpus_docs: list[Document],
    question: str,
    top_k: int | None = None,
) -> list[Document]:
    """BM25 sparse retrieval over a list of documents with Chinese tokenization."""
    top_k = top_k or settings.retrieval_top_k
    if not corpus_docs:
        return []

    tokenized_corpus = [_chinese_tokenize(doc.page_content) for doc in corpus_docs]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = _chinese_tokenize(question)
    scores = bm25.get_scores(tokenized_query)

    scored_docs = sorted(zip(corpus_docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored_docs[:top_k]]


def hybrid_merge(
    vector_results: list[Document],
    bm25_results: list[Document],
    top_k: int | None = None,
) -> list[Document]:
    """Merge vector and BM25 results using reciprocal rank fusion."""
    top_k = top_k or settings.retrieval_top_k
    rrf_constant = 60
    scores: dict[int, float] = {}
    doc_map: dict[int, Document] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = id(doc)
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (rrf_constant + rank + 1)
        doc_map[doc_id] = doc

    for rank, doc in enumerate(bm25_results):
        doc_id = id(doc)
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (rrf_constant + rank + 1)
        doc_map[doc_id] = doc

    sorted_ids = sorted(scores, key=lambda did: scores[did], reverse=True)
    return [doc_map[did] for did in sorted_ids[:top_k]]
