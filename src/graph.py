import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, START, END

from src.state import FraudState
from src.tools.transaction_analyzer import transaction_analyzer
from src.tools.customer_profile_tool import customer_profile_tool
from src.tools.merchant_risk_assessor import merchant_risk_assessor
from src.tools.velocity_checker import velocity_checker
from src.tools.rule_based_scorer import rule_based_scorer
from src.tools.ml_fraud_scorer import ml_fraud_scorer
from src.tools.action_decision_maker import action_decision_maker
from src.tools.report_generator import report_generator


def build_graph():
    """
    LangGraph StateGraph를 구성하고 컴파일해서 반환한다.
    - 노드: 8개 Tool 함수
    - 엣지: 순서대로 연결 (선형 파이프라인)
    """

    # ── 1. 그래프 객체 생성 ──────────────────────────────────
    # StateGraph(FraudState): 이 그래프가 FraudState를 공유 상태로 사용한다고 선언
    graph = StateGraph(FraudState)

    # ── 2. 노드 등록 ─────────────────────────────────────────
    # add_node("이름", 함수): 함수를 그래프의 노드로 등록
    # "이름"은 엣지 연결할 때 사용하는 식별자
    graph.add_node("transaction_analyzer",   transaction_analyzer)
    graph.add_node("customer_profile_tool",  customer_profile_tool)
    graph.add_node("merchant_risk_assessor", merchant_risk_assessor)
    graph.add_node("velocity_checker",       velocity_checker)
    graph.add_node("rule_based_scorer",      rule_based_scorer)
    graph.add_node("ml_fraud_scorer",        ml_fraud_scorer)
    graph.add_node("action_decision_maker",  action_decision_maker)
    graph.add_node("report_generator",       report_generator)

    # ── 3. 엣지 연결 (실행 순서 정의) ───────────────────────
    # add_edge("A", "B"): A가 끝나면 B를 실행
    # START: 그래프 시작점 (LangGraph 내장 상수)
    # END:   그래프 종료점 (LangGraph 내장 상수)
    graph.add_edge(START,                    "transaction_analyzer")
    graph.add_edge("transaction_analyzer",   "customer_profile_tool")
    graph.add_edge("customer_profile_tool",  "merchant_risk_assessor")
    graph.add_edge("merchant_risk_assessor", "velocity_checker")
    graph.add_edge("velocity_checker",       "rule_based_scorer")
    graph.add_edge("rule_based_scorer",      "ml_fraud_scorer")
    graph.add_edge("ml_fraud_scorer",        "action_decision_maker")
    graph.add_edge("action_decision_maker",  "report_generator")
    graph.add_edge("report_generator",       END)

    # ── 4. 컴파일 ────────────────────────────────────────────
    # compile(): 노드/엣지 구조를 검증하고 실행 가능한 객체로 변환
    return graph.compile()


# 모듈을 import할 때 그래프를 한 번만 빌드
# 다른 파일에서 "from src.graph import fraud_graph" 로 바로 사용
fraud_graph = build_graph()
