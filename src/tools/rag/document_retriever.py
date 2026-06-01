# src/tools/rag/document_retriever.py

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv()

_embeddings: Optional[HuggingFaceEmbeddings] = None
_case_retriever = None
_law_retriever = None


def _ensure_retrievers() -> bool:
    global _embeddings, _case_retriever, _law_retriever

    if _case_retriever is not None and _law_retriever is not None:
        return True

    qdrant_url = os.getenv("QDRANT_URL")
    if not qdrant_url:
        return False

    try:
        if _embeddings is None:
            _embeddings = HuggingFaceEmbeddings(
                model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
            )

        qdrant_client = QdrantClient(url=qdrant_url)

        case_vectorstore = QdrantVectorStore(
            client=qdrant_client,
            collection_name="case_chunks",
            embedding=_embeddings,
        )
        _case_retriever = case_vectorstore.as_retriever(search_kwargs={"k": 5})

        law_vectorstore = QdrantVectorStore(
            client=qdrant_client,
            collection_name="law_chunks",
            embedding=_embeddings,
        )
        _law_retriever = law_vectorstore.as_retriever(search_kwargs={"k": 4})
        return True
    except Exception:
        _case_retriever = None
        _law_retriever = None
        return False


def search_cases(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Qdrant에서 사례 검색."""

    if not _ensure_retrievers():
        return []

    try:
        results = _case_retriever.invoke(query)
    except Exception:
        return []

    formatted_results = []
    for doc in results[:top_k]:
        metadata = doc.metadata
        similarity_score = max(0.0, 1.0 - (metadata.get("_distance", 0.1) / 2))
        formatted_results.append(
            {
                "title": metadata.get("title", "제목 없음"),
                "source": metadata.get("source", "알 수 없음"),
                "snippet": doc.page_content,
                "similarity": similarity_score,
                "tags": metadata.get("tags", []),
                "year": metadata.get("year", 0),
                "geo_scope": metadata.get("geo_scope", "국제"),
            }
        )

    return formatted_results


def search_laws(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Qdrant에서 법령 검색."""

    if not _ensure_retrievers():
        return []

    try:
        results = _law_retriever.invoke(query)
    except Exception:
        return []

    formatted_results = []
    for doc in results[:top_k]:
        metadata = doc.metadata
        formatted_results.append(
            {
                "law_name": metadata.get("law_name", "알 수 없음"),
                "article_no": metadata.get("article_no", ""),
                "paragraph_no": metadata.get("paragraph_no", ""),
                "snippet": doc.page_content[:200],
                "source": "법령 DB",
            }
        )

    return formatted_results
