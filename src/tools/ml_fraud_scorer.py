import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.state import FraudState

# ── 모델 로드 ──────────────────────────────────────────────────────────
# ML 팀원이 학습시킨 LightGBM 모델을 불러온다.
# joblib: sklearn 계열 모델을 저장/불러오는 표준 라이브러리
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../data/fraud_model.pkl")

try:
    import joblib

    _model = joblib.load(_MODEL_PATH)
    _has_model = True
except FileNotFoundError:
    _model = None
    _has_model = False
except Exception:
    _model = None
    _has_model = False

# ── 피처 순서 정의 ─────────────────────────────────────────────────────
# ML 팀원(조진영)과 합의된 피처 순서 — 이 순서가 모델 학습 순서와 동일해야 한다.
# ⚠️ 절대 순서 바꾸지 말 것: 순서가 다르면 모델이 완전히 엉뚱한 값을 예측한다.
_FEATURE_NAMES = [
    "amt",                  # 1. 거래 금액
    "amount_ratio",         # 2. 고객 평균 대비 금액 비율 (현재금액 / 30일평균)
    "is_unusual_hour",      # 3. 비정상 시간대 여부 (0/1)
    "is_unusual_city",      # 4. 평소 외 지역 여부 (0/1)
    "is_unusual_category",  # 5. 평소 외 카테고리 여부 (0/1)
    "merchant_risk_score",  # 6. 가맹점 위험도 (low=0, medium=1, high=2)
    "avg_amount_30d",       # 7. 고객 30일 평균 금액
    "std_amount_30d",       # 8. 고객 30일 표준편차
]


def ml_fraud_scorer(state: FraudState) -> dict:
    """
    Tool 6: ML Fraud Scorer
    - 역할: LightGBM 모델로 사기 확률(0.0 ~ 1.0)을 예측한다.
    - LLM 사용: X (ML 모델 추론)
    - 읽는 State 필드: tx_features, customer_profile, merchant_risk
    - 쓰는 State 필드: ml_score
    """
    # 모델 파일이 없으면 None으로 처리 (ML 팀 작업 완료 전까지)
    if not _has_model:
        return {"ml_score": None}

    # ── 1. State에서 피처 추출 ───────────────────────────────
    features = _extract_features(state)

    # ── 2. 모델 입력 형태로 변환 ─────────────────────────────
    # _FEATURE_NAMES 순서대로 값을 뽑아 2차원 배열로 만든다.
    # [[v1, v2, v3, ...]] 형태: 행=거래 1건, 열=피처
    X = np.array([[features.get(name, 0.0) for name in _FEATURE_NAMES]])

    # ── 3. 예측 ──────────────────────────────────────────────
    try:
        # predict_proba → [[정상 확률, 사기 확률]]
        # [0][1]: 첫 번째(유일한) 거래의 사기 확률
        prob = float(_model.predict_proba(X)[0][1])
        return {"ml_score": round(prob, 4)}
    except Exception:
        return {"ml_score": None}


def _extract_features(state: FraudState) -> dict:
    """
    State의 여러 필드에서 모델 입력 피처를 하나의 딕셔너리로 모은다.
    _FEATURE_NAMES 순서와 키 이름이 정확히 일치해야 한다.

    Boolean → int 변환: ML 모델은 숫자만 받기 때문 (True→1, False→0)
    merchant_risk_level → 숫자 변환: low=0, medium=1, high=2
    """
    tx = state.get("tx_features") or {}
    cp = state.get("customer_profile") or {}
    mr = state.get("merchant_risk") or {}

    # 가맹점 위험도 문자열 → 숫자 변환 (ML 팀 합의: low=0, medium=1, high=2)
    _risk_map = {"low": 0, "medium": 1, "high": 2}
    merchant_risk_score = _risk_map.get(mr.get("risk_level", "low"), 0)

    # amount_ratio: 현재 거래금액 / 고객 30일 평균금액
    # 평균이 0이면 나누기 오류 방지 → max(..., 1.0) 처리
    amount = tx.get("amount", 0.0)
    avg_amount = cp.get("avg_amount_30d", 0.0)
    amount_ratio = amount / max(avg_amount, 1.0)

    return {
        "amt":                 amount,
        "amount_ratio":        round(amount_ratio, 4),
        "is_unusual_hour":     int(tx.get("is_night_transaction", False)),
        "is_unusual_city":     int(cp.get("is_unusual_city", False)),   # customer_profile_tool에서 채워줌
        "is_unusual_category": int(cp.get("is_unusual_category", False)),
        "merchant_risk_score": merchant_risk_score,
        "avg_amount_30d":      avg_amount,
        "std_amount_30d":      cp.get("std_amount_30d", 0.0),
    }
