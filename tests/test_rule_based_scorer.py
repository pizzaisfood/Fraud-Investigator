"""
Tool 5 (rule_based_scorer) 단위 테스트.

R001~R007 룰 조건 함수와 점수 누적 로직을 검증한다.

※ 테스트 환경 주의사항:
    data/fds_rules.csv 파일이 없을 때 _rules_meta = {} 로 초기화된다.
    CSV가 없으면 각 룰의 점수가 기본값 10으로 처리된다.
    → 이 테스트는 CSV 없이도 통과하도록 설계되어 있다 (Graceful Degradation 검증 포함).

실행: python -m pytest tests/ -v
"""

import pytest
from src.tools.rule_based_scorer import rule_based_scorer


def _state(tx_features=None, customer_profile=None, merchant_risk=None, velocity_signals=None):
    """
    최소 FraudState 빌더 — 필요한 필드만 채운다.
    나머지는 빈 딕셔너리({})로 채워서 KeyError가 나지 않게 한다.
    """
    return {
        "transaction": {},
        "tx_features": tx_features or {},
        "customer_profile": customer_profile or {},
        "merchant_risk": merchant_risk or {},
        "velocity_signals": velocity_signals or {},
    }


# ── 아무 룰도 발동 안 하는 기본 케이스 ────────────────────────────────

def test_no_rules_on_clean_state():
    """모든 필드가 비어있으면 룰 발동 없음, 점수 0"""
    result = rule_based_scorer(_state())
    assert result["rule_hits"] == []
    assert result["rule_score"] == 0.0


# ── R001: 거래금액이 신용한도의 80% 초과 ──────────────────────────────

def test_R001_fires_when_amount_exceeds_80_percent():
    """900 > 1000 * 0.8 = 800 → R001 발동"""
    result = rule_based_scorer(_state(
        customer_profile={"credit_limit": 1000},
        tx_features={"amount": 900},
    ))
    assert "R001" in result["rule_hits"]


def test_R001_does_not_fire_at_exact_boundary():
    """800 은 800 을 초과하지 않음 (strict >) → 발동 안 함"""
    result = rule_based_scorer(_state(
        customer_profile={"credit_limit": 1000},
        tx_features={"amount": 800},
    ))
    assert "R001" not in result["rule_hits"]


def test_R001_does_not_fire_when_no_credit_limit():
    """credit_limit=0 이면 limit > 0 조건 실패 → 발동 안 함 (ZeroDivisionError 방지)"""
    result = rule_based_scorer(_state(
        customer_profile={"credit_limit": 0},
        tx_features={"amount": 999},
    ))
    assert "R001" not in result["rule_hits"]


# ── R002: 새벽/야간 시간대 거래 ───────────────────────────────────────

def test_R002_fires_on_night_transaction():
    """is_night_transaction=True → R002 발동"""
    result = rule_based_scorer(_state(tx_features={"is_night_transaction": True}))
    assert "R002" in result["rule_hits"]


def test_R002_does_not_fire_on_daytime():
    """is_night_transaction=False → 발동 안 함"""
    result = rule_based_scorer(_state(tx_features={"is_night_transaction": False}))
    assert "R002" not in result["rule_hits"]


# ── R003: 평소 이용 카테고리 외 거래 ─────────────────────────────────

def test_R003_fires_on_unusual_category():
    result = rule_based_scorer(_state(customer_profile={"is_unusual_category": True}))
    assert "R003" in result["rule_hits"]


def test_R003_does_not_fire_on_usual_category():
    result = rule_based_scorer(_state(customer_profile={"is_unusual_category": False}))
    assert "R003" not in result["rule_hits"]


# ── R004: 고위험 가맹점 ────────────────────────────────────────────────

def test_R004_fires_on_high_risk_merchant():
    result = rule_based_scorer(_state(merchant_risk={"is_high_risk": True}))
    assert "R004" in result["rule_hits"]


# ── R005: 단시간 다중 거래 (velocity) ────────────────────────────────

def test_R005_fires_on_velocity_flag():
    result = rule_based_scorer(_state(velocity_signals={"velocity_flag": True}))
    assert "R005" in result["rule_hits"]


# ── R006: Z-score 이상 ────────────────────────────────────────────────

def test_R006_fires_when_z_score_exceeds_2():
    """z_score = 2.5 → |2.5| > 2.0 → R006 발동"""
    result = rule_based_scorer(_state(customer_profile={"amount_z_score": 2.5}))
    assert "R006" in result["rule_hits"]


def test_R006_fires_on_negative_z_score():
    """z_score = -3.0 → |−3.0| > 2.0 → R006 발동 (절댓값 체크)"""
    result = rule_based_scorer(_state(customer_profile={"amount_z_score": -3.0}))
    assert "R006" in result["rule_hits"]


def test_R006_does_not_fire_at_boundary():
    """z_score = 2.0 → |2.0| > 2.0 이 False → 발동 안 함 (strict >)"""
    result = rule_based_scorer(_state(customer_profile={"amount_z_score": 2.0}))
    assert "R006" not in result["rule_hits"]


# ── R007: 차지백 비율 높은 가맹점 ────────────────────────────────────

def test_R007_fires_on_high_chargeback():
    result = rule_based_scorer(_state(merchant_risk={"is_high_chargeback": True}))
    assert "R007" in result["rule_hits"]


# ── 점수 누적 + 다중 룰 ────────────────────────────────────────────────

def test_multiple_rules_accumulate_score():
    """
    R002 + R003 동시 발동.
    CSV 없으면 각 룰 점수 = 10 → 합계 20.0.
    이 테스트는 CSV 없이도 동작하도록 설계됨 (Graceful Degradation).
    """
    result = rule_based_scorer(_state(
        tx_features={"is_night_transaction": True},       # R002
        customer_profile={"is_unusual_category": True},  # R003
    ))
    assert "R002" in result["rule_hits"]
    assert "R003" in result["rule_hits"]
    # CSV 없으면 각 룰 기본점수 10 → 총 20.0
    assert result["rule_score"] == 20.0


def test_all_rules_fire():
    """
    R001~R007 전부 발동시키는 케이스.
    7개 룰 × 기본 10점 = 70.0.
    """
    result = rule_based_scorer(_state(
        tx_features={
            "amount": 900,                   # R001 조건
            "is_night_transaction": True,    # R002
        },
        customer_profile={
            "credit_limit": 1000,           # R001 조건
            "is_unusual_category": True,    # R003
            "amount_z_score": 3.0,          # R006
        },
        merchant_risk={
            "is_high_risk": True,           # R004
            "is_high_chargeback": True,     # R007
        },
        velocity_signals={
            "velocity_flag": True,          # R005
        },
    ))
    assert set(result["rule_hits"]) == {"R001", "R002", "R003", "R004", "R005", "R006", "R007"}
    assert result["rule_score"] == 70.0
