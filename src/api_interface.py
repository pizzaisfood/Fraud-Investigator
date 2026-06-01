"""
api_interface.py — BE 팀을 위한 단일 진입점

이 파일이 하는 일:
    BE 팀이 우리 LangGraph 파이프라인을 호출하는 창구 역할.
    BE 팀은 이 파일의 investigate_transaction() 함수 하나만 알면 된다.

왜 이 파일이 필요한가:
    - BE 팀이 fraud_graph, FraudState 등 내부 구조를 몰라도 되도록 숨긴다.
    - 입력은 TransactionInput (Pydantic), 출력은 FraudInvestigationResult (Pydantic)로 고정.
    - 내부 구현이 바뀌어도 이 파일의 함수 시그니처만 유지하면 BE 팀 코드는 수정 불필요.

BE 팀 사용법:
    from src.api_interface import investigate_transaction
    from src.schemas import TransactionInput

    tx = TransactionInput(
        trans_num="TXN-001",
        trans_date_trans_time="2024-03-15 02:47:33",
        cc_num=1234567890,
        merchant="fraud_Legit_Shopping",
        amt=1850.00,
        category="shopping_net",
        city="Seoul",
        state="KR",
    )
    result = investigate_transaction(tx)

    print(result.risk_level)       # "high"
    print(result.action_decision)  # "block"
    print(result.report)           # "## 사기 조사 리포트 ..."
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
# 왜 필요한가: "from src.graph import fraud_graph" 같은 import가
#              어느 폴더에서 실행해도 동작하려면 루트 경로를 알려줘야 한다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import fraud_graph
from src.schemas import TransactionInput, FraudInvestigationResult


def investigate_transaction(tx: TransactionInput) -> FraudInvestigationResult:
    """
    거래 1건을 받아 사기 조사를 수행하고 결과를 반환한다.

    이 함수가 내부적으로 하는 일:
        1. TransactionInput → dict 변환 (LangGraph가 dict를 받으므로)
        2. fraud_graph.invoke()로 8개 Tool 순서대로 실행
        3. 최종 State에서 결과 꺼내기
        4. FraudInvestigationResult로 포장해서 반환

    Args:
        tx: TransactionInput — BE 팀이 보내는 거래 데이터

    Returns:
        FraudInvestigationResult — 위험 등급, 권고 조치, 자연어 리포트 포함

    Raises:
        Exception: 파이프라인 실행 중 복구 불가능한 에러 발생 시
    """

    # ── 1단계: Pydantic 객체 → dict 변환 ──────────────────────────
    # 왜 변환하는가:
    #   LangGraph의 invoke()는 dict를 받는다.
    #   Pydantic 객체를 그대로 넣으면 에러가 난다.
    #   .model_dump()는 Pydantic 객체를 dict로 변환하는 메서드.
    transaction_dict = tx.model_dump()
    # 결과: {"trans_num": "TXN-001", "amt": 1850.0, ...}

    # ── 2단계: LangGraph 파이프라인 실행 ──────────────────────────
    # 왜 {"transaction": ...} 형태로 감싸는가:
    #   FraudState의 첫 번째 필드가 "transaction"이기 때문.
    #   LangGraph는 초기 State로 이 dict를 받는다.
    initial_state = {"transaction": transaction_dict}
    final_state = fraud_graph.invoke(initial_state)
    # final_state: 8개 Tool이 모두 실행된 후의 최종 FraudState dict

    # ── 3단계: 최종 State에서 결과 꺼내서 반환 ────────────────────
    # 왜 .get()을 쓰는가:
    #   혹시 Tool이 실패해서 필드가 없을 경우를 대비.
    #   .get("risk_level", "unknown")은
    #   "risk_level 키가 있으면 그 값, 없으면 'unknown'"이라는 뜻.
    return FraudInvestigationResult(
        risk_level=final_state.get("risk_level", "unknown"),
        action_decision=final_state.get("action_decision", "review"),
        report=final_state.get("report", "[리포트 생성 실패]"),
        rule_hits=final_state.get("rule_hits") or [],
        rule_score=final_state.get("rule_score") or 0.0,
        ml_score=final_state.get("ml_score"),  # 모델 없으면 None — Optional이라 OK
    )
