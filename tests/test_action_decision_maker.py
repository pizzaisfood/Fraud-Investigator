"""
Tool 7 (action_decision_maker) 단위 테스트.

4-tier 판단 로직을 경계값 중심으로 검증한다.
모든 케이스에서 rule_score와 ml_score 외 다른 State 필드는 무관함.

실행: python -m pytest tests/ -v
"""

import pytest
from src.tools.action_decision_maker import action_decision_maker


def _state(rule_score: float, ml_score):
    """최소 FraudState — rule_score, ml_score만 채운다."""
    return {"rule_score": rule_score, "ml_score": ml_score}


# ── Tier 1: 명확한 고위험 ──────────────────────────────────────────────

def test_tier1_rule_at_threshold():
    """rule=60 (HIGH 기준 정확히) → block"""
    result = action_decision_maker(_state(60, None))
    assert result == {"risk_level": "high", "action_decision": "block"}


def test_tier1_rule_above_threshold():
    """rule=80 (HIGH 초과) → block"""
    result = action_decision_maker(_state(80, 0.10))
    assert result == {"risk_level": "high", "action_decision": "block"}


def test_tier1_ml_at_threshold():
    """ml=0.80 (HIGH ML 기준 정확히), rule은 낮아도 → block"""
    result = action_decision_maker(_state(10, 0.80))
    assert result == {"risk_level": "high", "action_decision": "block"}


# ── Tier 1.5: 준고위험 (ELEVATED) ─────────────────────────────────────

def test_tier1_5_elevated_both_above():
    """rule=45, ml=0.60 (둘 다 ELEVATED 기준 정확히) → block"""
    result = action_decision_maker(_state(45, 0.60))
    assert result == {"risk_level": "high", "action_decision": "block"}


def test_tier1_5_elevated_rule_just_below():
    """rule=44 (ELEVATED 미달), ml=0.90 → 로우 아닌 경계 → medium"""
    result = action_decision_maker(_state(44, 0.90))
    # ml=0.90 >= HIGH_ML_THRESHOLD(0.80) → Tier 1b에서 걸림 → block
    # 이 케이스는 실제론 Tier 1b block
    assert result == {"risk_level": "high", "action_decision": "block"}


def test_tier1_5_elevated_ml_just_below():
    """rule=55, ml=0.59 (ELEVATED ML 미달) → medium"""
    result = action_decision_maker(_state(55, 0.59))
    assert result == {"risk_level": "medium", "action_decision": "review"}


def test_tier1_5_elevated_ml_none():
    """rule=55, ml=None (모델 없음) → ELEVATED 조건 불충족 → medium"""
    result = action_decision_maker(_state(55, None))
    assert result == {"risk_level": "medium", "action_decision": "review"}


# ── Tier 2: 명확한 저위험 ──────────────────────────────────────────────

def test_tier2_low_both_at_threshold():
    """rule=20, ml=0.30 (LOW 기준 정확히) → approve"""
    result = action_decision_maker(_state(20, 0.30))
    assert result == {"risk_level": "low", "action_decision": "approve"}


def test_tier2_low_ml_none():
    """rule=10, ml=None (모델 없음 = ml_is_low=True) → approve"""
    result = action_decision_maker(_state(10, None))
    assert result == {"risk_level": "low", "action_decision": "approve"}


def test_tier2_low_rule_just_above():
    """rule=21 (LOW 기준 초과), ml=0.10 → medium (저위험 미달)"""
    result = action_decision_maker(_state(21, 0.10))
    assert result == {"risk_level": "medium", "action_decision": "review"}


def test_tier2_low_ml_just_above():
    """rule=10, ml=0.31 (LOW ML 기준 초과) → medium"""
    result = action_decision_maker(_state(10, 0.31))
    assert result == {"risk_level": "medium", "action_decision": "review"}


# ── Tier 3: 경계선 (fallthrough) ──────────────────────────────────────

def test_tier3_pure_medium():
    """rule=35, ml=0.50 (어느 tier에도 해당 안 됨) → review"""
    result = action_decision_maker(_state(35, 0.50))
    assert result == {"risk_level": "medium", "action_decision": "review"}


def test_tier3_rule_59_no_model():
    """rule=59 (HIGH 바로 아래), ml=None → ELEVATED 조건 없음 → medium"""
    result = action_decision_maker(_state(59, None))
    assert result == {"risk_level": "medium", "action_decision": "review"}
