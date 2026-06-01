"""
Tool 6 (ml_fraud_scorer) 단위 테스트.

현재 data/fraud_model.pkl 파일이 없는 상태에서의 동작을 검증한다.
ML 팀(조진영)이 모델을 전달하면 추가 테스트를 붙일 수 있다.

테스트 설계 원칙:
    "파일이 없어도 파이프라인이 죽지 않는다" — Graceful Degradation 자동 검증.
    모델 없는 상태에서 ml_score=None을 반환하는 것이 핵심 계약(contract).

실행: python -m pytest tests/ -v
"""

import pytest
from src.tools.ml_fraud_scorer import ml_fraud_scorer, _has_model


def _minimal_state():
    """테스트용 최소 FraudState — 모든 피처 필드를 빈 딕셔너리로 채운다."""
    return {
        "transaction": {},
        "tx_features": {},
        "customer_profile": {},
        "merchant_risk": {},
        "velocity_signals": {},
    }


# ── Graceful Degradation: 모델 파일 없을 때 ──────────────────────────

def test_returns_none_when_no_model_file():
    """
    data/fraud_model.pkl 이 없으면 ml_score=None 반환.

    왜 이 테스트가 중요한가:
        ML 팀이 모델을 아직 전달 안 한 상태에서도 파이프라인이
        계속 동작해야 한다. ml_score=None이 되면 Tool 7이
        ml_score=None 케이스를 별도 처리하도록 설계되어 있다.

    이것이 "Graceful Degradation" 패턴 — 외부 의존성(모델 파일)이
    없어도 시스템 전체가 멈추지 않는다.
    """
    if _has_model:
        pytest.skip("모델 파일이 있어서 이 테스트는 건너뜁니다 (모델 로드 테스트 필요)")

    result = ml_fraud_scorer(_minimal_state())
    assert result == {"ml_score": None}


def test_returns_dict_with_ml_score_key():
    """
    반환값이 반드시 'ml_score' 키를 가진 딕셔너리여야 한다.
    Tool 7 (action_decision_maker)이 state.get("ml_score")로 접근하기 때문.
    """
    result = ml_fraud_scorer(_minimal_state())
    assert isinstance(result, dict)
    assert "ml_score" in result


# ── 모델 있을 때 테스트 (ML 팀 작업 완료 후 활성화) ──────────────────

@pytest.mark.skipif(not _has_model, reason="fraud_model.pkl 없으면 건너뜀")
def test_ml_score_is_probability_between_0_and_1():
    """
    모델이 있을 때: ml_score가 0.0~1.0 사이의 확률값이어야 한다.
    predict_proba()는 확률을 반환하므로 이 범위를 벗어날 수 없다.
    """
    result = ml_fraud_scorer(_minimal_state())
    score = result["ml_score"]
    assert score is not None
    assert 0.0 <= score <= 1.0


@pytest.mark.skipif(not _has_model, reason="fraud_model.pkl 없으면 건너뜀")
def test_ml_score_is_rounded_to_4_decimal_places():
    """
    round(prob, 4) 처리 → 소수점 4자리 이하 (0.8765 형태).
    리포트 텍스트에서 87.65% 같이 표시하기 위해 반올림 처리됨.
    """
    result = ml_fraud_scorer(_minimal_state())
    score = result["ml_score"]
    if score is not None:
        assert score == round(score, 4)
