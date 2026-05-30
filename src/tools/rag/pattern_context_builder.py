from datetime import datetime

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
    customer_profile = state.get("customer_profile") or {}
    velocity_signals = state.get("velocity_signals") or {}
    transaction = state.get("transaction") or {}

    amount = tx_features.get("amount") or transaction.get("amt") or transaction.get("amount") or 0
    category = tx_features.get("category") or transaction.get("category") or ""
    hour = tx_features.get("hour_of_day")
    month = None

    tx_time = transaction.get("trans_date_trans_time")
    if isinstance(tx_time, str):
        try:
            month = datetime.strptime(tx_time, "%Y-%m-%d %H:%M:%S").month
        except ValueError:
            month = None
    
    query_strategy = {
        "case_query": "",
        "should_search_law": False,
        "law_query": None,
        "priority_tags": [],
    }
    
    # ─────────────────────────────────────────────────────────
    # 패턴 1: 시간대 (T1)
    # ─────────────────────────────────────────────────────────
    if hour in {22, 23, 0, 1, 2, 3}:
        query_strategy["case_query"] = (
            f"time 야간 새벽 {hour}시 {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["time", "night"]

    # ─────────────────────────────────────────────────────────
    # 패턴 2: 계절성 시간 (T2)
    # ─────────────────────────────────────────────────────────
    elif month in {10, 11}:
        query_strategy["case_query"] = (
            f"time seasonal 가을 연말 {month}월 {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["time", "seasonal"]

    # ─────────────────────────────────────────────────────────
    # 패턴 3: 고액 (A1)
    # ─────────────────────────────────────────────────────────
    elif amount > 300:
        query_strategy["case_query"] = (
            f"amount high_value 고액 거래 {amount} {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["amount", "high_value"]

    # ─────────────────────────────────────────────────────────
    # 패턴 4: 소액 / 카드테스팅 (A2)
    # ─────────────────────────────────────────────────────────
    elif amount < 10:
        query_strategy["case_query"] = (
            f"amount low_value card_testing 소액 거래 {amount} {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["amount", "low_value", "card_testing"]

    # ─────────────────────────────────────────────────────────
    # 패턴 5: 가맹점 유형 (M1~M3)
    # ─────────────────────────────────────────────────────────
    elif category in {"shopping_net", "misc_net"}:
        query_strategy["case_query"] = (
            f"mcc ecommerce digital_goods 쇼핑 디지털 상품 {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["mcc", "ecommerce", "digital_goods"]
    elif category == "travel":
        query_strategy["case_query"] = (
            f"mcc hotel travel 호텔 여행 {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["mcc", "hotel", "travel"]
    elif category == "entertainment":
        query_strategy["case_query"] = (
            f"mcc gaming gambling 엔터테인먼트 게임 도박 {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["mcc", "gaming", "gambling"]

    # ─────────────────────────────────────────────────────────
    # 패턴 6: CNP / 원격 거래 (L1)
    # ─────────────────────────────────────────────────────────
    elif "_net" in category:
        query_strategy["case_query"] = (
            f"location remote CNP 원격 거래 {transaction.get('merchant', '')} {category}"
        )
        query_strategy["priority_tags"] = ["location", "remote", "cnp"]

    # ─────────────────────────────────────────────────────────
    # 기본 쿼리 (패턴 미감지)
    # ─────────────────────────────────────────────────────────
    else:
        query_strategy["case_query"] = (
            f"{transaction.get('merchant', '')} {category} 사기 사례"
        )
        query_strategy["priority_tags"] = []
    
    # ─────────────────────────────────────────────────────────
    # 법령 검색 조건: 매우 비정상적인 거래 + 고위험
    # ─────────────────────────────────────────────────────────
    rule_score = state.get("rule_score") or 0
    ml_score = state.get("ml_score") or 0
    
    if rule_score > 70 or ml_score > 0.85:  # 매우 고위험
        query_strategy["should_search_law"] = True
        query_strategy["law_query"] = "자금세탁 거래 모니터링 비정상적 거래"
    
    return query_strategy