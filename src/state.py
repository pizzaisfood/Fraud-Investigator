from typing import Any, Dict, List, Optional, TypedDict


class FraudState(TypedDict):
    """
    LangGraph의 8개 Tool이 공유하는 상태(State) 스키마.
    Tool이 실행될수록 아래 필드들이 하나씩 채워진다.
    """

    # ── 입력 ──────────────────────────────────────────────────
    # 분석 대상 거래 정보. 파이프라인 시작 시 외부에서 주입된다.
    # 예: {"trans_num": "abc", "amount": 150.0, "merchant": "fraud_shop", ...}
    transaction: Dict[str, Any]

    # ── Tool 1: Transaction Analyzer ──────────────────────────
    # 거래의 기본 특징을 LLM이 해석한 결과
    # 예: {"hour_of_day": 3, "is_foreign": True, "amount_category": "large"}
    tx_features: Optional[Dict[str, Any]]

    # ── Tool 2: Customer Profile Tool ─────────────────────────
    # customer_profiles.csv에서 조회한 해당 고객의 평소 패턴
    # 예: {"avg_amount_30d": 85.0, "credit_limit": 5000, "usual_categories": ["grocery"]}
    customer_profile: Optional[Dict[str, Any]]

    # ── Tool 3: Merchant Risk Assessor ────────────────────────
    # merchant_risk.csv에서 조회한 가맹점 위험도 정보
    # 예: {"risk_level": "high", "chargeback_rate": 0.12, "fraud_report_count": 47}
    merchant_risk: Optional[Dict[str, Any]]

    # ── Tool 4: Velocity Checker ──────────────────────────────
    # 최근 거래 빈도 분석 결과 (단시간 다중 거래 = 위험 신호)
    # 예: {"txn_last_1h": 5, "txn_last_24h": 12, "velocity_flag": True}
    velocity_signals: Optional[Dict[str, Any]]

    # ── Tool 5: Rule-based Scoring ────────────────────────────
    # fds_rules.csv의 R001~R007 룰 중 발동된 항목과 누적 점수
    rule_hits: Optional[List[str]]  # 예: ["R001", "R004", "R007"]
    rule_score: Optional[float]  # 예: 75.0  (점수가 높을수록 위험)

    # ── Tool 6: ML Fraud Scorer ───────────────────────────────
    # LightGBM 모델이 예측한 사기 확률 (0.0 ~ 1.0)
    ml_score: Optional[float]  # 예: 0.87

    # ── Tool 7: Action Decision Maker ─────────────────────────
    # Rule Score + ML Score를 종합해 내린 최종 판단
    risk_level: Optional[str]  # "high" | "medium" | "low"
    action_decision: Optional[str]  # "block" | "review" | "approve"

    # ── Tool 8: Report Generator ──────────────────────────────
    # GPT-4o가 모든 분석 결과를 바탕으로 작성한 자연어 조사 리포트
    report: Optional[str]
