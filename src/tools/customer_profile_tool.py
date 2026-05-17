import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.state import FraudState

# ── 데이터 로드: 모듈이 import될 때 딱 한 번만 실행된다 ────────────
# 매 Tool 호출마다 CSV를 읽으면 느리기 때문에, 메모리에 한 번만 올려둔다.
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data")
_CSV_PATH = os.path.join(_DATA_PATH, "customer_profiles.csv")

try:
    _customer_df = pd.read_csv(_CSV_PATH)
    # cc_num을 인덱스로 설정 → 조회 속도 O(1)로 향상
    _customer_df = _customer_df.set_index("cc_num")
except FileNotFoundError:
    # 데이터 파일이 없을 때 빈 DataFrame으로 대체 (프로그램이 crash하지 않도록)
    _customer_df = pd.DataFrame()


def customer_profile_tool(state: FraudState) -> dict:
    """
    Tool 2: Customer Profile Tool
    - 역할: CSV에서 해당 고객의 평소 패턴을 조회하고, 현재 거래와 비교한다.
    - LLM 사용: X (CSV 조회 + 수치 계산)
    - 읽는 State 필드: tx_features (cc_num, amount 사용)
    - 쓰는 State 필드: customer_profile
    """
    tx_features = state["tx_features"]
    cc_num = tx_features.get("cc_num")

    # ── 1. 고객 데이터 조회 ──────────────────────────────────
    if _customer_df.empty or cc_num not in _customer_df.index:
        # 고객 정보가 없으면 None 반환 → 이후 Tool이 None 체크 후 처리
        return {"customer_profile": None}

    row = _customer_df.loc[cc_num]

    # ── 2. Z-score 계산: 현재 거래가 평소와 얼마나 다른가 ───
    # Z = (현재값 - 평균) / 표준편차
    # |Z| > 2 이면 약 95% 확률로 비정상 거래
    current_amount = tx_features.get("amount", 0)
    avg = float(row["avg_amount_30d"])
    std = float(row["std_amount_30d"])
    z_score = (current_amount - avg) / std if std > 0 else 0.0

    # ── 3. 카테고리 이상 감지 ────────────────────────────────
    # usual_categories는 CSV에 문자열로 저장됨 → eval()로 리스트로 변환
    try:
        usual_categories = eval(str(row["usual_categories"]))
    except Exception:
        usual_categories = []

    current_category = tx_features.get("category", "")
    is_unusual_category = current_category not in usual_categories

    # ── 4. 결과 딕셔너리 구성 ────────────────────────────────
    customer_profile = {
        "cc_num": cc_num,
        "avg_amount_30d": avg,
        "std_amount_30d": std,
        "home_city": str(row.get("home_city", "")),
        "usual_categories": usual_categories,
        "usual_active_hours": str(row.get("usual_active_hours", "")),
        "avg_daily_txn_count": float(row.get("avg_daily_txn_count", 0)),
        "credit_limit": float(row.get("credit_limit", 0)),
        # 비교 신호 (이후 Tool들이 판단에 활용)
        "amount_z_score": round(z_score, 2),
        "is_amount_anomalous": abs(z_score) > 2,
        "is_unusual_category": is_unusual_category,
    }

    return {"customer_profile": customer_profile}
