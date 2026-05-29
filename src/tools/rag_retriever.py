# src/tools/rag_retriever.py

from typing import Optional, List, Dict, Any
from src.state import FraudState
from src.tools.rag.pattern_context_builder import _build_rag_query_strategy
from src.tools.rag.document_retriever import search_cases
from src.tools.rag.legislation_retriever import search_laws_hybrid


def rag_retriever(state: FraudState) -> dict:
    """
    Tool 6.5: RAG Retriever (LangGraph Tool)
    
    - 읽는 State: transaction, tx_features, merchant_risk, velocity_signals
    - 쓰는 State: rag_evidence (List[Dict] or None)
    
    RAG 팀 인터페이스 가이드 준수:
      ✅ 단일 함수로 모든 RAG 로직 처리
      ✅ rag_evidence 스키마 정확히 준수
      ✅ None 반환 시 파이프라인이 gracefully 처리
    """
    
    try:
        # Step 1: 패턴 감지 & 쿼리 전략 수립
        query_strategy = _build_rag_query_strategy(state)
        
        # Step 2: 사례 검색 (항상 수행)
        case_results = search_cases(
            query=query_strategy["case_query"],
            top_k=5
        )
        
        # Step 3: 법령 검색 (조건부)
        law_results = []
        if query_strategy["should_search_law"] and query_strategy["law_query"]:
            law_results = search_laws_hybrid(
                query=query_strategy["law_query"]
            )
        
        # Step 4: 결과를 rag_evidence 스키마로 변환
        rag_evidence = _format_rag_evidence(
            case_results=case_results,
            law_results=law_results,
            priority_tags=query_strategy["priority_tags"]
        )
        
        # Step 5: 최대 5개까지만 반환 (인터페이스 가이드 권장)
        return {"rag_evidence": rag_evidence[:5] if rag_evidence else None}
    
    except Exception as e:
        print(f"RAG Retriever 오류: {e}")
        # 오류 시 None → 파이프라인이 gracefully 처리
        return {"rag_evidence": None}


def _format_rag_evidence(
    case_results: List[Dict],
    law_results: List[Dict],
    priority_tags: List[str]
) -> Optional[List[Dict[str, Any]]]:
    """
    사례 + 법령 결과를 rag_evidence 스키마로 변환
    
    출력 스키마 (RAG 팀 인터페이스 가이드):
    {
        "source": str,
        "snippet": str,
        "similarity": float,
        "tags": list[str],
    }
    """
    
    evidence_list = []
    
    # ─────────────────────────────────────────────────────────
    # 사례 결과 변환
    # ─────────────────────────────────────────────────────────
    for case in case_results:
        # 국내/해외 표시 포함
        geo_scope = case.get("geo_scope", "국제")
        if geo_scope == "국내":
            source_text = f"국내 사기 DB: {case.get('title', '')}"
        else:
            source_text = f"해외 보고서: {case.get('source', '')} ({case.get('year', '')})"
        
        tags = case.get("tags", [])
        # priority_tags에 있는 것을 맨 앞에 배치
        tags = sorted(
            tags,
            key=lambda t: (t not in priority_tags, tags.index(t) if t in tags else 999)
        )
        
        evidence_list.append({
            "source": source_text,
            "snippet": case.get("snippet", ""),
            "similarity": case.get("similarity", 0.0),
            "tags": tags,
        })
    
    # ─────────────────────────────────────────────────────────
    # 법령 결과 변환 (law_results가 있을 경우)
    # ─────────────────────────────────────────────────────────
    for law in law_results:
        law_snippet = (
            f"제{law.get('article_no')}조 {law.get('law_name')} - "
            f"{law.get('main_paragraph', '')}"
        )
        
        evidence_list.append({
            "source": f"법령: {law.get('law_name', '')}",
            "snippet": law_snippet,
            "similarity": 0.95,  # 법령은 정확도 높으므로 높은 점수
            "tags": ["legislation"],
        })
    
    return evidence_list if evidence_list else None