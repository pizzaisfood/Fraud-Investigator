import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import fraud_graph

# streamlit에서 쓸 필드만 골라냄 (나중에 state 바뀌면 여기 수정)
_KEYS = [
    "risk_level",
    "action_decision",
    "rule_hits",
    "rule_score",
    "ml_score",
    "report",
    "tx_features",
    "customer_profile",
    "merchant_risk",
    "velocity_signals",
]


def investigate(transaction: dict) -> dict:
    """거래 dict 넣으면 graph 돌리고 결과만 dict로 반환"""
    if not transaction:
        raise ValueError("transaction 비어있음")

    out = fraud_graph.invoke({"transaction": transaction})
    return {k: out.get(k) for k in _KEYS}


def sample_transaction():
    # README에 있는 예시 그대로
    return {
        "trans_num": "abc123",
        "trans_date_trans_time": "2020-06-21 03:14:25",
        "cc_num": 123456789,
        "merchant": "fraud_Shop_Name",
        "amt": 1500.0,
        "category": "shopping_net",
        "city": "Seoul",
        "state": "KR",
    }
