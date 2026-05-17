import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from src.state import FraudState

# ── 거래 이력 CSV 로드 (있을 때만) ──────────────────────────────────
# 실제 거래 이력이 있어야 velocity를 정확히 계산할 수 있다.
# 없으면 고객 프로필의 평균값으로 추론하는 모드로 전환된다.
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data")
_CSV_PATH = os.path.join(_DATA_PATH, "transaction_history.csv")

try:
    _history_df = pd.read_csv(_CSV_PATH)
    _history_df["trans_date_trans_time"] = pd.to_datetime(
        _history_df["trans_date_trans_time"]
    )
    _has_history = True
except FileNotFoundError:
    _history_df = pd.DataFrame()
    _has_history = False


def velocity_checker(state: FraudState) -> dict:
    """
    Tool 4: Velocity Checker
    - 역할: 동일 카드의 최근 거래 빈도를 분석한다 (단시간 다중 거래 = 사기 신호).
    - LLM 사용: X (시간 윈도우 계산)
    - 읽는 State 필드: transaction, tx_features, customer_profile
    - 쓰는 State 필드: velocity_signals
    """
    tx_features = state["tx_features"]
    customer_profile = state.get("customer_profile") or {}

    cc_num = tx_features.get("cc_num")
    current_time_str = state["transaction"].get("trans_date_trans_time", "")

    # ── 모드 선택 ──────────────────────────────────────────────────
    if _has_history and not _history_df.empty:
        return _check_with_history(cc_num, current_time_str, customer_profile)
    else:
        return _check_with_profile(customer_profile)


def _check_with_history(cc_num, current_time_str: str, customer_profile: dict) -> dict:
    """
    모드 1: 실제 거래 이력 CSV가 있을 때
    - 현재 거래 시각 기준으로 1시간, 24시간 이내 동일 카드 거래 수를 센다.
    """
    try:
        current_dt = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return _fallback_signals()

    # 동일 카드 거래만 필터링
    card_history = _history_df[_history_df["cc_num"] == cc_num].copy()

    # 시간 윈도우 경계 계산
    # timedelta: 시간 간격을 나타내는 객체. datetime에서 빼면 과거 시점이 된다.
    one_hour_ago = current_dt - timedelta(hours=1)
    one_day_ago  = current_dt - timedelta(hours=24)

    # 각 윈도우 안에 들어오는 거래 건수
    txn_last_1h  = len(card_history[card_history["trans_date_trans_time"] >= one_hour_ago])
    txn_last_24h = len(card_history[card_history["trans_date_trans_time"] >= one_day_ago])

    avg_daily = float(customer_profile.get("avg_daily_txn_count", 3.0))

    # 위험 판단 기준:
    # - 1시간 내 3건 이상: 짧은 시간 집중 거래 (burst)
    # - 24시간 내 거래수가 평소 2배 초과: 비정상적 활동
    is_burst         = txn_last_1h >= 3
    is_daily_anomaly = txn_last_24h > avg_daily * 2
    velocity_flag    = is_burst or is_daily_anomaly

    return {
        "velocity_signals": {
            "mode":                "history",
            "txn_last_1h":         txn_last_1h,
            "txn_last_24h":        txn_last_24h,
            "avg_daily_txn_count": avg_daily,
            "is_burst":            is_burst,
            "is_daily_anomaly":    is_daily_anomaly,
            "velocity_flag":       velocity_flag,
        }
    }


def _check_with_profile(customer_profile: dict) -> dict:
    """
    모드 2: 거래 이력 CSV가 없을 때
    - 정확한 건수는 알 수 없으므로 None으로 표기하고 flag는 False로 처리.
    - 이 사실을 mode 필드에 기록해 이후 Report Generator가 참고할 수 있게 한다.
    """
    avg_daily = float(customer_profile.get("avg_daily_txn_count", 3.0))

    return {
        "velocity_signals": {
            "mode":                "profile_inference",
            "txn_last_1h":         None,   # 이력 없음 → 알 수 없음
            "txn_last_24h":        None,
            "avg_daily_txn_count": avg_daily,
            "is_burst":            False,
            "is_daily_anomaly":    False,
            "velocity_flag":       False,
        }
    }


def _fallback_signals() -> dict:
    """시각 파싱 실패 등 예외 상황 — 최소한의 안전한 기본값."""
    return {
        "velocity_signals": {
            "mode":                "fallback",
            "txn_last_1h":         None,
            "txn_last_24h":        None,
            "avg_daily_txn_count": None,
            "is_burst":            False,
            "is_daily_anomaly":    False,
            "velocity_flag":       False,
        }
    }
