# src/tools/rag/document_retriever.py

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# ─────────────────────────────────────────────────────────
# 초기화 (한 번만 실행)
# ─────────────────────────────────────────────────────────
_embeddings = HuggingFaceEmbeddings(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
)
_qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"))

_case_vectorstore = QdrantVectorStore(
    client=_qdrant_client,
    collection_name="case_chunks",
    embedding=_embeddings,
)
_case_retriever = _case_vectorstore.as_retriever(search_kwargs={"k": 5})

_law_vectorstore = QdrantVectorStore(
    client=_qdrant_client,
    collection_name="law_chunks",
    embedding=_embeddings,
)
_law_retriever = _law_vectorstore.as_retriever(search_kwargs={"k": 4})


def search_cases(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Qdrant에서 사례 검색 (rag_experiment2.ipynb의 search_cases 참고)
    
    반환:
        [{
            "title": str,
            "source": str,
            "snippet": str,
            "similarity": float,
            "tags": list[str],
            "year": int,
            "geo_scope": str,  # "국내" or "해외"
        }]
    """
    results = _case_retriever.invoke(query)
    
    formatted_results = []
    for i, doc in enumerate(results[:top_k]):
        metadata = doc.metadata
        
        # Qdrant 거리값 → 유사도 점수로 변환 (0.0 ~ 1.0)
        # 주의: Qdrant는 거리(distance)를 반환하므로, 유사도로 변환
        similarity_score = max(0.0, 1.0 - (metadata.get("_distance", 0.1) / 2))
        
        formatted_results.append({
            "title": metadata.get("title", "제목 없음"),
            "source": metadata.get("source", "알 수 없음"),
            "snippet": doc.page_content[:300],  # 처음 300자
            "similarity": similarity_score,
            "tags": metadata.get("tags", []),
            "year": metadata.get("year", 0),
            "geo_scope": metadata.get("geo_scope", "국제"),  # "국내" or "해외"
        })
    
    return formatted_results


def search_laws(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Qdrant에서 법령 검색 (rag_experiment2.ipynb의 search_law 참고)
    
    반환:
        [{
            "law_name": str,
            "article_no": int,
            "paragraph_no": str,
            "snippet": str,
            "source": str,  # "자금세탁 방지 규정" 등
        }]
    """
    results = _law_retriever.invoke(query)
    
    formatted_results = []
    for doc in results[:top_k]:
        metadata = doc.metadata
        
        formatted_results.append({
            "law_name": metadata.get("law_name", "알 수 없음"),
            "article_no": metadata.get("article_no", ""),
            "paragraph_no": metadata.get("paragraph_no", ""),
            "snippet": doc.page_content[:200],
            "source": "법령 DB",
        })
    
    return formatted_results