import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.state import FraudState

# ── fds_rules.csv 로드: 룰 ID → {name, score, severity} 매핑 ─────────
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data")
_CSV_PATH = os.path.join(_DATA_PATH, "fds_rules.csv")

try:
    _rules_df = pd.read_csv(_CSV_PATH).set_index("rule_id")
    _rules_meta = _rules_df.to_dict(orient="index")  # {"R001": {"score": 30, ...}, ...}
except FileNotFoundError:
    _rules_meta = {}


# ══════════════════════════════════════════════════════════════════════
# 룰 조건 함수 (R001, R002, R004~R007 — R003은 ML팀 결정으로 폐기)
# 각 함수는 FraudState를 받아 조건이 충족되면 True를 반환한다.
# ══════════════════════════════════════════════════════════════════════


def _check_R001(state: FraudState) -> bool:
    """R001: 고액 이상거래 — 거래금액이 고객 30일 평균의 5배 이상"""
    cp = state.get("customer_profile") or {}
    tx = state.get("tx_features") or {}
    avg = cp.get("avg_amount_30d", 0)
    amount = tx.get("amount", 0)
    # avg가 0이면 (프로필 없음/신규고객) 5배 기준이 무의미 → 발동 안 함
    return avg > 0 and amount >= avg * 5


def _check_R002(state: FraudState) -> bool:
    """R002: 비정상 시간대 — 새벽/심야 거래 (hour<6 or hour>=22)"""
    tx = state.get("tx_features") or {}
    # is_night_transaction은 transaction_analyzer가 (hour<6 or hour>=22)로 계산해줌
    return tx.get("is_night_transaction", False)


def _check_R004(state: FraudState) -> bool:
    """R004: 고위험 가맹점 — risk_level=high 가맹점 거래"""
    mr = state.get("merchant_risk") or {}
    return mr.get("is_high_risk", False)


def _check_R005(state: FraudState) -> bool:
    """R005: 짧은 시간 반복 거래 — 10분 내 3건 이상 (velocity_flag)"""
    vs = state.get("velocity_signals") or {}
    return vs.get("velocity_flag", False)


def _check_R006(state: FraudState) -> bool:
    """R006: 한도 근접 거래 — 거래 금액이 카드 한도의 70% 이상"""
    cp = state.get("customer_profile") or {}
    tx = state.get("tx_features") or {}
    limit = cp.get("credit_limit", 0)
    amount = tx.get("amount", 0)
    return limit > 0 and amount >= limit * 0.7


def _check_R007(state: FraudState) -> bool:
    """R007: 평소 미사용 카테고리 — usual_categories 상위 5개에 없는 카테고리"""
    cp = state.get("customer_profile") or {}
    # is_unusual_category는 customer_profile_tool이 계산해줌 (CSV의 usual_categories 기준)
    return cp.get("is_unusual_category", False)


# 룰 ID → 조건 함수 매핑 테이블
_RULE_CHECKS = {
    "R001": _check_R001,
    "R002": _check_R002,
    "R004": _check_R004,
    "R005": _check_R005,
    "R006": _check_R006,
    "R007": _check_R007,
}


# ══════════════════════════════════════════════════════════════════════
# 메인 Tool 함수
# ══════════════════════════════════════════════════════════════════════


def rule_based_scorer(state: FraudState) -> dict:
    """
    Tool 5: Rule-based Scorer
    - 역할: 6개 FDS 룰(R001, R002, R004~R007)을 순서대로 평가 — R003은 폐기됨
    - LLM 사용: X (규칙 기반 계산)
    - 읽는 State 필드: tx_features, customer_profile, merchant_risk, velocity_signals
    - 쓰는 State 필드: rule_hits, rule_score
    """
    rule_hits = []  # 발동된 룰 ID 목록
    rule_score = 0.0  # 누적 위험 점수

    for rule_id, check_fn in _RULE_CHECKS.items():
        if check_fn(state):  # 조건이 True이면 룰 발동
            rule_hits.append(rule_id)

            # CSV에서 읽은 점수를 더함. CSV 없으면 기본 10점.
            score = float(_rules_meta.get(rule_id, {}).get("score", 10))
            rule_score += score

    return {
        "rule_hits": rule_hits,
        "rule_score": round(rule_score, 2),
    }
