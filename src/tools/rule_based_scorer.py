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
# 룰 조건 함수 (R001 ~ R007)
# 각 함수는 FraudState를 받아 조건이 충족되면 True를 반환한다.
# ══════════════════════════════════════════════════════════════════════


def _check_R001(state: FraudState) -> bool:
    """R001: 거래금액이 신용한도의 80%를 초과"""
    cp = state.get("customer_profile") or {}
    tx = state.get("tx_features") or {}
    limit = cp.get("credit_limit", 0)
    amount = tx.get("amount", 0)
    return limit > 0 and amount > limit * 0.8


def _check_R002(state: FraudState) -> bool:
    """R002: 새벽 시간대(00~05시, 22~23시) 거래"""
    tx = state.get("tx_features") or {}
    return tx.get("is_night_transaction", False)


def _check_R003(state: FraudState) -> bool:
    """R003: 평소 이용 카테고리 외 거래"""
    cp = state.get("customer_profile") or {}
    return cp.get("is_unusual_category", False)


def _check_R004(state: FraudState) -> bool:
    """R004: 고위험(high) 가맹점에서의 거래"""
    mr = state.get("merchant_risk") or {}
    return mr.get("is_high_risk", False)


def _check_R005(state: FraudState) -> bool:
    """R005: 단시간 다중 거래 (velocity_flag 발동)"""
    vs = state.get("velocity_signals") or {}
    return vs.get("velocity_flag", False)


def _check_R006(state: FraudState) -> bool:
    """R006: 평소 거래금액 대비 Z-score 2.0 초과 (통계적 이상)"""
    cp = state.get("customer_profile") or {}
    z_score = cp.get("amount_z_score", 0.0)
    return abs(z_score) > 2.0


def _check_R007(state: FraudState) -> bool:
    """R007: 차지백(Chargeback) 비율이 높은 가맹점"""
    mr = state.get("merchant_risk") or {}
    return mr.get("is_high_chargeback", False)


# 룰 ID → 조건 함수 매핑 테이블
_RULE_CHECKS = {
    "R001": _check_R001,
    "R002": _check_R002,
    "R003": _check_R003,
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
    - 역할: R001~R007 룰을 순서대로 평가하고 발동된 룰의 점수를 누적한다.
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
