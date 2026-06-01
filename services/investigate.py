import copy
import os
import sys
from datetime import datetime
from typing import Callable, Optional

from dotenv import load_dotenv

from src.tools.rag_retriever import rag_retriever

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

from src.api_interface import investigate_transaction
from src.schemas import FraudInvestigationResult, TransactionInput

NODE_DEFINITIONS = [
    ("transaction_analyzer", "거래 분석", "tx_features"),
    ("customer_profile_tool", "고객 프로필", "customer_profile"),
    ("merchant_risk_assessor", "가맹점 위험도", "merchant_risk"),
    ("velocity_checker", "거래 빈도", "velocity_signals"),
    ("rule_based_scorer", "룰 스코어", "rule_score"),
    ("ml_fraud_scorer", "ML 점수", "ml_score"),
    ("rag_retriever", "RAG 검색", "rag_evidence"), 
    ("action_decision_maker", "최종 판단", "action_decision"),
    ("report_generator", "리포트 생성", "report"),
]


def _offline_mode():
    return os.getenv("OFFLINE_TEST", "").lower() in ("1", "true", "yes")


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
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "offline"

    import src.tools.action_decision_maker as adm
    import src.tools.report_generator as rg

    adm.action_decision_maker = _mock_action_decision
    rg.report_generator = _mock_report


def ensure_runtime_ready():
    """UI trace 실행 전 오프라인 mock 등 런타임 준비."""
    if _offline_mode():
        _setup_offline_graph()


def _result_from_state(state: dict) -> dict:
    return FraudInvestigationResult(
        risk_level=state.get("risk_level", "unknown"),
        action_decision=state.get("action_decision", "review"),
        report=state.get("report", "[리포트 생성 실패]"),
        rule_hits=state.get("rule_hits") or [],
        rule_score=state.get("rule_score") or 0.0,
        ml_score=state.get("ml_score"),
    ).model_dump()


def _get_pipeline_nodes():
    ensure_runtime_ready()
    from src.tools.action_decision_maker import action_decision_maker
    from src.tools.customer_profile_tool import customer_profile_tool
    from src.tools.merchant_risk_assessor import merchant_risk_assessor
    from src.tools.ml_fraud_scorer import ml_fraud_scorer
    from src.tools.report_generator import report_generator
    from src.tools.rule_based_scorer import rule_based_scorer
    from src.tools.transaction_analyzer import transaction_analyzer
    from src.tools.velocity_checker import velocity_checker

    node_map = {
        "transaction_analyzer": transaction_analyzer,
        "customer_profile_tool": customer_profile_tool,
        "merchant_risk_assessor": merchant_risk_assessor,
        "velocity_checker": velocity_checker,
        "rule_based_scorer": rule_based_scorer,
        "ml_fraud_scorer": ml_fraud_scorer,
        "rag_retriever": rag_retriever,    
        "action_decision_maker": action_decision_maker,
        "report_generator": report_generator,
    }

    return [
        {
            "id": node_id,
            "label": label,
            "focus_key": focus_key,
            "func": node_map[node_id],
        }
        for node_id, label, focus_key in NODE_DEFINITIONS
    ]


def _build_request_record(
    transaction: dict, state: dict, node_traces: list[dict], request_id: Optional[str] = None
) -> dict:
    return {
        "request_id": request_id or datetime.now().strftime("REQ-%Y%m%d-%H%M%S-%f"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed",
        "transaction": transaction,
        "result": _result_from_state(state),
        "node_traces": node_traces,
        "state": state,
    }


def investigate(transaction: dict) -> dict:
    if not transaction:
        raise ValueError("transaction 비어있음")

    tx = TransactionInput.model_validate(transaction)
    return investigate_transaction(tx).model_dump()


def investigate_with_trace(
    transaction: dict,
    on_step: Optional[Callable[[dict, int, int, dict], None]] = None,
    on_step_start: Optional[Callable[[dict, int, int, dict], None]] = None,
    on_step_end: Optional[Callable[[dict, int, int, dict], None]] = None,
    request_id: Optional[str] = None,
) -> dict:
    if not transaction:
        raise ValueError("transaction 비어있음")

    ensure_runtime_ready()
    state = {"transaction": copy.deepcopy(transaction)}
    node_traces = []
    pipeline_nodes = _get_pipeline_nodes()
    total = len(pipeline_nodes)

    for index, node in enumerate(pipeline_nodes, start=1):
        running_trace = {
            "id": node["id"],
            "label": node["label"],
            "status": "running",
            "step": index,
            "total_steps": total,
            "focus_key": node["focus_key"],
            "updates": {},
            "focus_data": None,
        }
        if on_step_start:
            on_step_start(copy.deepcopy(running_trace), index, total, copy.deepcopy(state))
        elif on_step:
            on_step(copy.deepcopy(running_trace), index, total, copy.deepcopy(state))

        updates = node["func"](state)
        state.update(updates)

        trace = {
            "id": node["id"],
            "label": node["label"],
            "status": "completed",
            "step": index,
            "total_steps": total,
            "focus_key": node["focus_key"],
            "updates": copy.deepcopy(updates),
            "focus_data": copy.deepcopy(state.get(node["focus_key"])),
        }
        node_traces.append(trace)

        if on_step_end:
            on_step_end(copy.deepcopy(trace), index, total, copy.deepcopy(state))
        elif on_step:
            on_step(copy.deepcopy(trace), index, total, copy.deepcopy(state))

    return _build_request_record(transaction, copy.deepcopy(state), node_traces, request_id)


def sample_transaction():
    return {
        "trans_num": "DEMO-REAL-001",
        "trans_date_trans_time": "2020-06-21 03:14:25",
        "cc_num": 60416207185,
        "merchant": "fraud_Altenwerth, Cartwright and Koss",
        "amt": 1500.0,
        "category": "shopping_net",
        "city": "Fort Washakie",
        "state": "WY",
    }
