import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

_graph = None

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


def _offline_mode():
    if os.getenv("OFFLINE_TEST", "").lower() in ("1", "true", "yes"):
        return True
    return not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY")


def _mock_action_decision(state: dict) -> dict:
    rule_score = float(state.get("rule_score") or 0)
    ml_score = state.get("ml_score")
    rule_hits = state.get("rule_hits") or []

    if rule_score >= 60:
        return {"risk_level": "high", "action_decision": "block"}
    if ml_score is not None and ml_score >= 0.8:
        return {"risk_level": "high", "action_decision": "block"}
    if rule_score <= 20 and (ml_score is None or ml_score <= 0.3):
        return {"risk_level": "low", "action_decision": "approve"}
    if rule_score >= 40 or (ml_score is not None and ml_score >= 0.5) or rule_hits:
        return {"risk_level": "medium", "action_decision": "review"}
    return {"risk_level": "low", "action_decision": "approve"}


def _mock_report(state: dict) -> dict:
    tx = state.get("tx_features") or {}
    rule_hits = state.get("rule_hits") or []
    rule_score = state.get("rule_score") or 0
    ml_score = state.get("ml_score")
    risk = state.get("risk_level", "?")
    action = state.get("action_decision", "?")
    ml_txt = f"{ml_score * 100:.1f}%" if ml_score is not None else "N/A"

    text = f"""## 사기 조사 리포트 (오프라인 테스트)

거래: {tx.get("trans_num", "?")} / ${tx.get("amount", 0):.2f} / {tx.get("merchant", "?")}

- 위험 등급: {risk}
- 조치: {action}
- 룰 점수: {rule_score} (hits: {", ".join(rule_hits) or "없음"})
- ML: {ml_txt}

※ BE 테스트용 mock — Gemini 미호출
"""
    return {"report": text}


def _setup_offline_graph():
    # 팀장 tool import 시 키 검증만 통과시키기 위함 (실제 호출 안 함)
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "offline"

    import src.tools.action_decision_maker as adm
    import src.tools.report_generator as rg

    adm.action_decision_maker = _mock_action_decision
    rg.report_generator = _mock_report


def _get_graph():
    global _graph
    if _graph is not None:
        return _graph

    if _offline_mode():
        _setup_offline_graph()

    from src.graph import fraud_graph

    _graph = fraud_graph
    return _graph


def investigate(transaction: dict) -> dict:
    if not transaction:
        raise ValueError("transaction 비어있음")

    out = _get_graph().invoke({"transaction": transaction})
    return {k: out.get(k) for k in _KEYS}


def sample_transaction():
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
