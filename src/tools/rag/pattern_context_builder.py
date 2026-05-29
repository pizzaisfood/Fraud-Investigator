from src.state import FraudState


def _build_rag_query_strategy(state: FraudState) -> dict:
    """
    State 분석 → 어떤 패턴이 감지되었는가?
    → 검색할 쿼리와 retriever 선택
    
    출력: {
        "case_query": str,              # Qdrant 사례 검색 쿼리
        "should_search_law": bool,      # Neo4j 법령 검색 여부
        "law_query": str or None,       # 법령 검색 쿼리 (if needed)
        "priority_tags": list[str],     # 이 tags를 가진 결과 우선
    }
    """
    
    tx_features = state.get("tx_features") or {}
    merchant_risk = state.get("merchant_risk") or {}
    velocity_signals = state.get("velocity_signals") or {}
    transaction = state.get("transaction") or {}
    
    query_strategy = {
        "case_query": "",
        "should_search_law": False,
        "law_query": None,
        "priority_tags": [],
    }
    
    # ─────────────────────────────────────────────────────────
    # 패턴 1: 소액 반복 실패 (Velocity 이상)
    # ─────────────────────────────────────────────────────────
    if velocity_signals.get("velocity_flag") and velocity_signals.get("txn_last_1h", 0) >= 3:
        query_strategy["case_query"] = (
            f"카드 테스팅 소액 거래 반복 {transaction.get('merchant', '')} "
            f"{transaction.get('category', '')}"
        )
        query_strategy["priority_tags"] = ["velocity", "card_testing"]
    
    # ─────────────────────────────────────────────────────────
    # 패턴 2: 평소 대비 고액 + 환금성 높은 업종
    # ─────────────────────────────────────────────────────────
    elif (tx_features.get("is_amount_anomalous") and 
          transaction.get("category") in ["jewelry", "giftcard", "luxury"]):
        query_strategy["case_query"] = (
            f"고액 거래 {transaction.get('category')} 가맹점 "
            f"사기 탐지 {transaction.get('amount', 0)}"
        )
        query_strategy["priority_tags"] = ["large_amount", "merchant_risk"]
    
    # ─────────────────────────────────────────────────────────
    # 패턴 3: 새벽/야간 거래
    # ─────────────────────────────────────────────────────────
    elif tx_features.get("is_night_transaction"):
        query_strategy["case_query"] = (
            f"야간 새벽 거래 {transaction.get('merchant', '')} "
            f"{transaction.get('category', '')}"
        )
        query_strategy["priority_tags"] = ["night_transaction"]
    
    # ─────────────────────────────────────────────────────────
    # 패턴 4: 비정상적 지역 거래
    # ─────────────────────────────────────────────────────────
    elif tx_features.get("is_unusual_location"):
        query_strategy["case_query"] = (
            f"해외 거래 비정상 지역 {transaction.get('state', '')} "
            f"{transaction.get('city', '')}"
        )
        query_strategy["priority_tags"] = ["unusual_location"]
    
    # ─────────────────────────────────────────────────────────
    # 기본 쿼리 (패턴 미감지)
    # ─────────────────────────────────────────────────────────
    else:
        query_strategy["case_query"] = (
            f"{transaction.get('merchant', '')} "
            f"{transaction.get('category', '')} 사기 사례"
        )
        query_strategy["priority_tags"] = []
    
    # ─────────────────────────────────────────────────────────
    # 법령 검색 조건: 매우 비정상적인 거래 + 고위험
    # ─────────────────────────────────────────────────────────
    rule_score = state.get("rule_score", 0)
    ml_score = state.get("ml_score", 0)
    
    if rule_score > 70 or ml_score > 0.85:  # 매우 고위험
        query_strategy["should_search_law"] = True
        query_strategy["law_query"] = "자금세탁 거래 모니터링 비정상적 거래"
    
    return query_strategy