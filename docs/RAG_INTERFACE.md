# RAG 팀 인터페이스 가이드

> LangGraph 파이프라인에 RAG 결과를 연결하는 방법을 설명합니다.

---

## RAG가 파이프라인에서 하는 역할

```
Tool 6 (ML 점수) → [RAG: rag_evidence 채우기] → Tool 7 (최종 판단) → Tool 8 (리포트)
```

Tool 7(GPT 판단)과 Tool 8(리포트 작성)이 `rag_evidence`를 읽어서  
**"과거에 유사한 사기 사례가 있었는가"** 를 판단 근거로 활용합니다.

---

## 채워야 할 State 필드: `rag_evidence`

### 타입

```python
rag_evidence: Optional[List[Dict[str, Any]]]
```

- 검색 결과가 있으면 → 리스트 반환 (최대 5개)
- 검색 결과가 없거나 오류 발생 시 → `None` 반환 (파이프라인이 None을 graceful하게 처리함)

---

### 각 항목의 형식

```python
{
    "source":     str,    # 출처 (예: "EBA 2025 Report", "내부 사기 DB")
    "snippet":    str,    # 관련 내용 요약 (2~3문장)
    "similarity": float,  # 유사도 점수 0.0 ~ 1.0
    "tags":       list[str],  # 관련 위험 태그
}
```

### 예시

```python
rag_evidence = [
    {
        "source": "EBA 2025 Payment Fraud Report",
        "snippet": "단기간 다중 거래(Card Testing)는 도난 카드 유효성 검증 수법으로, "
                   "주로 소액 → 대액 순서로 진행된다. 1시간 내 5건 이상 발생 시 고위험.",
        "similarity": 0.91,
        "tags": ["velocity", "card_testing"],
    },
    {
        "source": "내부 사기 DB",
        "snippet": "동일 가맹점(fraud_Electronics)에서 2023년 11월 유사 패턴 43건 탐지. "
                   "평균 거래금액 $1,200 이상, 새벽 2~4시 집중.",
        "similarity": 0.84,
        "tags": ["merchant_risk", "night_transaction"],
    },
]
```

---

## LangGraph Tool로 구현하는 방법

RAG 팀이 만들 Tool의 시그니처:

```python
# src/tools/rag_retriever.py

from src.state import FraudState

def rag_retriever(state: FraudState) -> dict:
    """
    Tool 6.5: RAG Retriever
    - 읽는 State 필드: transaction, tx_features, merchant_risk
    - 쓰는 State 필드: rag_evidence
    """
    transaction = state.get("transaction") or {}
    tx_features = state.get("tx_features") or {}

    # 쿼리 생성 — 가맹점명, 카테고리, 금액을 기반으로 유사 사례 검색
    query = f"{transaction.get('merchant')} {transaction.get('category')} {transaction.get('amt')}"

    try:
        results = your_vector_db.search(query, top_k=5)
        evidence = [
            {
                "source":     r.metadata["source"],
                "snippet":    r.page_content,
                "similarity": r.score,
                "tags":       r.metadata.get("tags", []),
            }
            for r in results
        ]
        return {"rag_evidence": evidence if evidence else None}

    except Exception:
        return {"rag_evidence": None}  # 오류 시 None → 파이프라인 계속 진행
```

---

## graph.py 등록 방법

LLM 팀장(이정훈)에게 완성된 `rag_retriever` 함수를 전달하면  
`src/graph.py`에 Tool 6과 Tool 7 사이에 노드로 등록합니다.

직접 등록이 필요한 경우:

```python
# src/graph.py 에 추가
from src.tools.rag_retriever import rag_retriever

graph.add_node("rag_retriever", rag_retriever)
graph.add_edge("ml_fraud_scorer", "rag_retriever")   # 기존 엣지 삭제 후
graph.add_edge("rag_retriever", "action_decision_maker")
```

---

## tags 목록 (권장)

일관성을 위해 아래 태그를 우선 사용하세요.

| 태그 | 의미 |
|---|---|
| `velocity` | 단시간 다중 거래 패턴 |
| `card_testing` | 소액 → 대액 카드 유효성 검증 수법 |
| `merchant_risk` | 고위험 가맹점 관련 사례 |
| `night_transaction` | 새벽/야간 거래 |
| `large_amount` | 고액 거래 이상 패턴 |
| `unusual_location` | 비정상 지역 거래 |
| `account_takeover` | 계정 탈취 의심 |
