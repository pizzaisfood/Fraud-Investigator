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
# ⚠️ ML 팀원과 반드시 합의 필요: 모델 학습 시 사용한 피처 순서와 동일해야 한다.
# 순서가 다르면 모델이 엉뚱한 값을 예측한다.
_FEATURE_NAMES = [
    "amount",  # 거래 금액
    "hour_of_day",  # 거래 시각 (0~23)
    "is_night_transaction",  # 새벽/밤 거래 여부 (0 or 1)
    "is_weekend",  # 주말 여부 (0 or 1)
    "amount_z_score",  # 평소 대비 금액 편차 (Z-score)
    "avg_amount_30d",  # 고객 30일 평균 거래금액
    "credit_limit",  # 신용한도
    "fraud_report_count",  # 가맹점 사기 신고 건수
    "chargeback_rate",  # 가맹점 차지백 비율
    "avg_daily_txn_count",  # 고객 일평균 거래 건수
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
    Boolean 값은 int로 변환한다 (True→1, False→0).
    ML 모델은 숫자만 받기 때문이다.
    """
    tx = state.get("tx_features") or {}
    cp = state.get("customer_profile") or {}
    mr = state.get("merchant_risk") or {}

    return {
        "amount": tx.get("amount", 0.0),
        "hour_of_day": float(tx.get("hour_of_day", 0)),
        "is_night_transaction": int(tx.get("is_night_transaction", False)),
        "is_weekend": int(tx.get("is_weekend", False)),
        "amount_z_score": cp.get("amount_z_score", 0.0),
        "avg_amount_30d": cp.get("avg_amount_30d", 0.0),
        "credit_limit": cp.get("credit_limit", 0.0),
        "fraud_report_count": float(mr.get("fraud_report_count", 0)),
        "chargeback_rate": mr.get("chargeback_rate", 0.0),
        "avg_daily_txn_count": cp.get("avg_daily_txn_count", 0.0),
    }
