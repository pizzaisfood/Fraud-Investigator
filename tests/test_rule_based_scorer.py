"""
Tool 5 (rule_based_scorer) 단위 테스트.

ML 팀 fds_rules.csv (룰 엔진 v3) 기준으로 검증한다.
6개 룰 체제: R001, R002, R004, R005, R006, R007 (R003 폐기).

점수 검증은 _rules_meta(= fds_rules.csv 로드 결과)를 직접 참조해
CSV 유무와 무관하게 통과하도록 설계한다.
  - CSV 없으면: 각 룰 기본 10점
  - CSV 있으면: R001=25, R002=10, R004=25, R005=20, R006=15, R007=2

실행: python -m pytest tests/ -v
"""

import pytest
from src.tools.rule_based_scorer import rule_based_scorer, _rules_meta


def _state(tx_features=None, customer_profile=None, merchant_risk=None, velocity_signals=None):
    """최소 FraudState 빌더 — 필요한 필드만 채우고 나머지는 빈 dict."""
    return {
        "transaction": {},
        "tx_features": tx_features or {},
        "customer_profile": customer_profile or {},
        "merchant_risk": merchant_risk or {},
        "velocity_signals": velocity_signals or {},
    }


def _expected_score(rule_ids):
    """
    발동한 룰들의 점수 합을 계산한다.
    fds_rules.csv가 있으면 그 점수를, 없으면 기본 10점을 사용한다.
    → 테스트가 CSV 유무에 흔들리지 않게 하는 방어적 패턴.
    """
    return round(sum(float(_rules_meta.get(r, {}).get("score", 10)) for r in rule_ids), 2)


# ── 기본: 아무 룰도 발동 안 함 ──────────────────────────────────────
def test_no_rules_on_clean_state():
    result = rule_based_scorer(_state())
    assert result["rule_hits"] == []
    assert result["rule_score"] == 0.0


# ── R001: 고액 이상거래 (amount >= avg_amount_30d * 5) ───────────────
def test_R001_fires_at_5x_average():
    # avg=100 → 임계 500. ×5는 정수배라 float 오차 없음 → 경계값(500) 테스트 가능.
    result = rule_based_scorer(_state(
        customer_profile={"avg_amount_30d": 100.0},
        tx_features={"amount": 500.0},
    ))
    assert "R001" in result["rule_hits"]


def test_R001_does_not_fire_below_5x():
    result = rule_based_scorer(_state(
        customer_profile={"avg_amount_30d": 100.0},
        tx_features={"amount": 499.0},
    ))
    assert "R001" not in result["rule_hits"]


def test_R001_does_not_fire_when_no_average():
    # avg=0 (프로필 없음) → 가드(avg>0)에 막혀 발동 안 함
    result = rule_based_scorer(_state(
        customer_profile={"avg_amount_30d": 0},
        tx_features={"amount": 9999.0},
    ))
    assert "R001" not in result["rule_hits"]


# ── R002: 비정상 시간대 ───────────────────────────────────────────────
def test_R002_fires_on_night():
    result = rule_based_scorer(_state(tx_features={"is_night_transaction": True}))
    assert "R002" in result["rule_hits"]


def test_R002_does_not_fire_on_daytime():
    result = rule_based_scorer(_state(tx_features={"is_night_transaction": False}))
    assert "R002" not in result["rule_hits"]


# ── R003 폐기 확인 ────────────────────────────────────────────────────
def test_R003_never_fires():
    # R003은 ML팀 결정으로 폐기됨 (합성데이터에서 city==home_city 100% 매칭 문제).
    # 과거 R003 트리거 신호(is_unusual_category)를 줘도 R003은 절대 등장하면 안 된다.
    result = rule_based_scorer(_state(
        customer_profile={"is_unusual_category": True},
    ))
    assert "R003" not in result["rule_hits"]


# ── R004: 고위험 가맹점 ───────────────────────────────────────────────
def test_R004_fires_on_high_risk_merchant():
    result = rule_based_scorer(_state(merchant_risk={"is_high_risk": True}))
    assert "R004" in result["rule_hits"]


# ── R005: 짧은 시간 반복 거래 ────────────────────────────────────────
def test_R005_fires_on_velocity_flag():
    result = rule_based_scorer(_state(velocity_signals={"velocity_flag": True}))
    assert "R005" in result["rule_hits"]


# ── R006: 한도 근접 거래 (amount >= credit_limit * 0.7) ──────────────
# 주의: ×0.7은 이진 부동소수점으로 정확히 떨어지지 않는다 (700*0.7 = 489.9999...).
#       따라서 경계값(정확히 70%) 테스트는 피하고, 명확히 위/아래인 값만 쓴다.
def test_R006_fires_clearly_above_70pct():
    result = rule_based_scorer(_state(
        customer_profile={"credit_limit": 1000.0},
        tx_features={"amount": 800.0},  # 800 >= 700 명확
    ))
    assert "R006" in result["rule_hits"]


def test_R006_does_not_fire_clearly_below_70pct():
    result = rule_based_scorer(_state(
        customer_profile={"credit_limit": 1000.0},
        tx_features={"amount": 600.0},  # 600 < 700 명확
    ))
    assert "R006" not in result["rule_hits"]


def test_R006_does_not_fire_when_no_limit():
    result = rule_based_scorer(_state(
        customer_profile={"credit_limit": 0},
        tx_features={"amount": 9999.0},
    ))
    assert "R006" not in result["rule_hits"]


# ── R007: 평소 미사용 카테고리 (옛 R003 역할 흡수) ──────────────────
def test_R007_fires_on_unusual_category():
    result = rule_based_scorer(_state(customer_profile={"is_unusual_category": True}))
    assert "R007" in result["rule_hits"]


def test_R007_does_not_fire_on_usual_category():
    result = rule_based_scorer(_state(customer_profile={"is_unusual_category": False}))
    assert "R007" not in result["rule_hits"]


# ── 점수 누적 + 다중 룰 ───────────────────────────────────────────────
def test_multiple_rules_accumulate_score():
    # R002(야간) + R007(미사용 카테고리) 동시 발동
    result = rule_based_scorer(_state(
        tx_features={"is_night_transaction": True},
        customer_profile={"is_unusual_category": True},
    ))
    assert set(result["rule_hits"]) == {"R002", "R007"}
    assert result["rule_score"] == _expected_score(["R002", "R007"])


def test_all_six_rules_fire():
    # 6개 룰을 모두 발동시키는 케이스.
    # amount=500: R001 임계(avg100*5=500) 충족 + R006 임계(limit700*0.7≈490) 충족
    result = rule_based_scorer(_state(
        tx_features={
            "amount": 500.0,
            "is_night_transaction": True,    # R002
        },
        customer_profile={
            "avg_amount_30d": 100.0,         # R001 임계 500
            "credit_limit": 700.0,           # R006 임계 ≈490
            "is_unusual_category": True,     # R007
        },
        merchant_risk={
            "is_high_risk": True,            # R004
        },
        velocity_signals={
            "velocity_flag": True,           # R005
        },
    ))
    assert set(result["rule_hits"]) == {"R001", "R002", "R004", "R005", "R006", "R007"}
    assert result["rule_score"] == _expected_score(
        ["R001", "R002", "R004", "R005", "R006", "R007"]
    )
