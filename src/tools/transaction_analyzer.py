import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from src.state import FraudState


def transaction_analyzer(state: FraudState) -> dict:
    """
    Tool 1: Transaction Analyzer
    - 역할: 원시 거래 데이터에서 분석에 필요한 특징(feature)을 추출한다.
    - LLM 사용: X (단순 계산 → 비용 절감)
    - 읽는 State 필드: transaction
    - 쓰는 State 필드: tx_features
    """
    tx = state["transaction"]

    # ── 1. 거래 시각 파싱 ────────────────────────────────────
    # 문자열 "2020-06-21 12:14:25" → datetime 객체로 변환
    try:
        dt = datetime.strptime(tx["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        day_of_week = dt.strftime("%A")   # "Monday", "Saturday" 등
        is_night = hour < 6 or hour >= 22  # 새벽 0~5시, 밤 22~23시
        is_weekend = dt.weekday() >= 5     # 5=토요일, 6=일요일
    except (KeyError, ValueError):
        hour, day_of_week, is_night, is_weekend = -1, "unknown", False, False

    # ── 2. 거래 금액 분류 ────────────────────────────────────
    # 숫자 금액을 카테고리로 변환 → 이후 LLM이 이해하기 쉬운 형태
    amount = float(tx.get("amt", 0))
    if amount < 10:
        amount_category = "micro"       # 10달러 미만
    elif amount < 100:
        amount_category = "small"       # 10~99달러
    elif amount < 500:
        amount_category = "medium"      # 100~499달러
    elif amount < 2000:
        amount_category = "large"       # 500~1999달러
    else:
        amount_category = "very_large"  # 2000달러 이상

    # ── 3. 결과를 tx_features 딕셔너리에 담기 ───────────────
    tx_features = {
        "trans_num":             tx.get("trans_num"),
        "cc_num":                tx.get("cc_num"),
        "merchant":              tx.get("merchant"),
        "amount":                amount,
        "amount_category":       amount_category,
        "hour_of_day":           hour,
        "day_of_week":           day_of_week,
        "is_night_transaction":  is_night,
        "is_weekend":            is_weekend,
        "category":              tx.get("category"),
        "city":                  tx.get("city"),
        "state":                 tx.get("state"),
    }

    # LangGraph 규칙: 수정할 State 필드만 딕셔너리로 리턴
    return {"tx_features": tx_features}
