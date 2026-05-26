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

    # ── 3. 엣지 연결 (의존성 기반 병렬 실행) ───────────────────────
    # LangGraph의 fan-out / fan-in 패턴:
    #   fan-out: 한 노드 → 여러 노드   → 두 노드가 병렬로 실행된다
    #   fan-in:  여러 노드 → 한 노드   → 두 노드가 모두 끝나야 다음이 시작된다
    #
    # 실제 의존성 그래프:
    #
    #   START → T1(분석)
    #             ├──→ T2(고객) ─┬──→ T4(빈도) → T5(룰) ─┐
    #             └──→ T3(가맹) ─┤                        ├──→ T7(판단) → T8(리포트) → END
    #                            └──→ T6(ML) ─────────────┘
    #
    # T2와 T3: 둘 다 tx_features만 읽음 → 병렬 실행 가능
    # T4와 T6: 둘 다 customer_profile+merchant_risk 읽음 → 병렬 실행 가능
    # T7: rule_score(T5)와 ml_score(T6)를 모두 필요로 함 → fan-in으로 대기

    # Layer 1: 시작 → T1 (단독)
    graph.add_edge(START, "transaction_analyzer")

    # Layer 2: T1 → T2, T3 (fan-out: 병렬 실행)
    graph.add_edge("transaction_analyzer", "customer_profile_tool")
    graph.add_edge("transaction_analyzer", "merchant_risk_assessor")

    # Layer 3: T2+T3 → T4 (fan-in: 둘 다 끝나야 T4 시작)
    #          T2+T3 → T6 (fan-in: 둘 다 끝나야 T6 시작, T4와 병렬)
    graph.add_edge("customer_profile_tool",  "velocity_checker")
    graph.add_edge("merchant_risk_assessor", "velocity_checker")
    graph.add_edge("customer_profile_tool",  "ml_fraud_scorer")
    graph.add_edge("merchant_risk_assessor", "ml_fraud_scorer")

    # Layer 4: T4 → T5 (순차: T5는 velocity_signals 필요)
    graph.add_edge("velocity_checker", "rule_based_scorer")

    # Layer 5: T5+T6 → T7 (fan-in: 둘 다 끝나야 최종 판단 가능)
    graph.add_edge("rule_based_scorer", "action_decision_maker")
    graph.add_edge("ml_fraud_scorer",   "action_decision_maker")

    # Layer 6: T7 → T8 → END (순차)
    graph.add_edge("action_decision_maker", "report_generator")
    graph.add_edge("report_generator",      END)

    # ── 4. 컴파일 ────────────────────────────────────────────
    # compile(): 노드/엣지 구조를 검증하고 실행 가능한 객체로 변환
    return graph.compile()


# 모듈을 import할 때 그래프를 한 번만 빌드
# 다른 파일에서 "from src.graph import fraud_graph" 로 바로 사용
fraud_graph = build_graph()
