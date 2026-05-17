import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.state import FraudState

# ── 모듈 로드 시 1회만 CSV 읽기 ─────────────────────────────────────
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data")
_CSV_PATH = os.path.join(_DATA_PATH, "merchant_risk.csv")

try:
    _merchant_df = pd.read_csv(_CSV_PATH)
except FileNotFoundError:
    _merchant_df = pd.DataFrame()


def merchant_risk_assessor(state: FraudState) -> dict:
    """
    Tool 3: Merchant Risk Assessor
    - 역할: CSV에서 가맹점의 위험도 정보를 조회하고, 없으면 기본값으로 처리한다.
    - LLM 사용: X (CSV 조회)
    - 읽는 State 필드: tx_features (merchant, category 사용)
    - 쓰는 State 필드: merchant_risk
    """
    tx_features = state["tx_features"]
    merchant_name = tx_features.get("merchant", "")

    # ── 1. 데이터 없음 처리 ─────────────────────────────────
    if _merchant_df.empty:
        return {"merchant_risk": _default_risk(merchant_name, tx_features)}

    # ── 2. 정확한 이름으로 조회 ─────────────────────────────
    row = _merchant_df[_merchant_df["merchant_name"] == merchant_name]

    # ── 3. 정확한 매칭 실패 → 부분 문자열로 재시도 ──────────
    # 거래 데이터의 merchant 이름과 DB의 merchant_name이 미묘하게 다를 수 있음
    # 예: 거래 = "fraud_Acme Corp"  /  DB = "Acme Corp"
    if row.empty:
        row = _merchant_df[
            _merchant_df["merchant_name"].str.contains(
                merchant_name, case=False, na=False
            )
        ]

    # ── 4. 그래도 없으면 Graceful Degradation ───────────────
    # 프로그램을 멈추지 않고, "정보 없음" 상태로 기본값을 넣어 계속 진행
    if row.empty:
        return {"merchant_risk": _default_risk(merchant_name, tx_features)}

    # ── 5. 조회 성공 → 결과 구성 ────────────────────────────
    row = row.iloc[0]  # 여러 행이 매칭되면 첫 번째만 사용

    chargeback_rate = float(row.get("chargeback_rate", 0.0))
    risk_level = str(row.get("risk_level", "medium"))

    merchant_risk = {
        "merchant_name": merchant_name,
        "found_in_db": True,
        "merchant_category": str(row.get("merchant_category", "")),
        "fraud_report_count": int(row.get("fraud_report_count", 0)),
        "chargeback_rate": chargeback_rate,
        "risk_level": risk_level,
        # 이후 Rule-based Scoring이 바로 읽을 수 있는 Boolean 플래그
        "is_high_risk": risk_level == "high",
        "is_high_chargeback": chargeback_rate > 0.05,  # 5% 초과 = 위험
    }

    return {"merchant_risk": merchant_risk}


def _default_risk(merchant_name: str, tx_features: dict) -> dict:
    """가맹점 DB에 정보가 없을 때 사용하는 기본값."""
    return {
        "merchant_name": merchant_name,
        "found_in_db": False,  # DB에 없었다는 사실을 기록
        "merchant_category": tx_features.get("category", "unknown"),
        "fraud_report_count": 0,
        "chargeback_rate": 0.0,
        "risk_level": "medium",  # 정보 없으면 중간 위험도로 가정
        "is_high_risk": False,
        "is_high_chargeback": False,
    }
