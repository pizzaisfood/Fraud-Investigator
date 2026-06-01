# src/tools/rag/legislation_retriever.py

import os
from typing import List, Dict, Any, Optional
from anyio.functools import lru_cache
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from src.tools.rag.document_retriever import search_laws

load_dotenv()

# ─────────────────────────────────────────────────────────
# Neo4j Graph 초기화
# ─────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _get_neo4j_graph():
    try:
        return Neo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
        )
    except Exception as exc:
        print(f"Neo4j 연결 실패: {exc}")
        return None

def _retrieve_related_articles(article_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Neo4j Graph에서 같은 법령의 관련 조항들 조회
    (rag_experiment2.ipynb의 graph_retrieve_by_article 참고)
    """
    if not article_ids:
        return []
    
    neo4j_graph = _get_neo4j_graph()
    if neo4j_graph is None:
        return []
    
    cypher = """
    UNWIND $article_ids AS article_id
    MATCH (a:Article {article_id: article_id})-[:HAS_PARAGRAPH]->(p:Paragraph)
    RETURN article_id, collect({paragraph_no: p.paragraph_no, text: p.text}) AS paragraphs
    LIMIT 10
    """
    
    try:
        results = neo4j_graph.query(cypher, {"article_ids": article_ids})
        return results
    except Exception as e:
        print(f"Neo4j 쿼리 실패: {e}")
        return []


def search_laws_hybrid(query: str) -> List[Dict[str, Any]]:
    """
    하이브리드 법령 검색:
    1. Vector 검색 (Qdrant) → 관련 법령 조항 찾기
    2. Graph 검색 (Neo4j) → 같은 법령의 전체 맥락 파악
    
    반환:
        [{
            "law_name": str,
            "article_no": int,
            "main_paragraph": str,  # 벡터 검색에서 나온 주요 조항
            "related_paragraphs": list[str],  # 같은 법령의 관련 조항들
            "source": "법령 DB",
        }]
    """
    # Step 1: Vector 검색
    vector_results = search_laws(query, top_k=3)
    
    if not vector_results:
        return []
    
    # Step 2: article_id 수집
    article_ids = [
        r.get("article_no")  # article_id 대신 article_no 사용
        for r in vector_results
        if r.get("article_no")
    ]
    
    # Step 3: Graph 검색 (관련 조항들)
    graph_results = _retrieve_related_articles(article_ids)
    
    # Step 4: 통합 포맷팅
    formatted_results = []
    for i, v_result in enumerate(vector_results):
        # 같은 법령의 그래프 결과 찾기
        graph_context = next(
            (g for g in graph_results if g.get("article_id") == v_result.get("article_no")),
            {}
        )
        
        related_paras = []
        for para_dict in graph_context.get("paragraphs", []):
            if para_dict.get("text") and para_dict["text"] != "삭제":
                related_paras.append(f"제{para_dict.get('paragraph_no')}항: {para_dict['text'][:100]}")
        
        formatted_results.append({
            "law_name": v_result.get("law_name"),
            "article_no": v_result.get("article_no"),
            "main_paragraph": v_result.get("snippet"),
            "related_paragraphs": related_paras[:2],  # 관련 조항 2개까지만
            "source": "법령 DB (자금세탁방지법)",
        })
    
    return formatted_results