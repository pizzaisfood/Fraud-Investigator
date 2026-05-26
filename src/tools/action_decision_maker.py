import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.state import FraudState

load_dotenv()  # .env 파일에서 GENAI_TEAM09 (OpenAI API 키) 로드

# ── 판단 기준 임계값 ────────────────────────────────────────────────
# 이 값들을 바꾸면 전체 시스템의 민감도가 바뀐다.
HIGH_RULE_THRESHOLD = 60  # 룰 점수 60 이상 → 명확한 고위험
HIGH_ML_THRESHOLD = 0.80  # ML 확률 80% 이상 → 명확한 고위험
LOW_RULE_THRESHOLD = 20  # 룰 점수 20 이하
LOW_ML_THRESHOLD = 0.30  # ML 확률 30% 이하 → 둘 다 낮으면 저위험

# ── LLM 초기화 ──────────────────────────────────────────────────────
# temperature=0: 창의성 없이 일관된 판단을 내리게 설정
_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=os.environ.get("GENAI_TEAM09"),
)


def action_decision_maker(state: FraudState) -> dict:
    """
    Tool 7: Action Decision Maker
    - 역할: rule_score + ml_score를 종합해 최종 위험 등급과 조치를 결정한다.
    - LLM 사용: O (경계선 케이스에서 GPT-4o 판단)
    - 읽는 State 필드: rule_score, rule_hits, ml_score, tx_features, customer_profile, merchant_risk
    - 쓰는 State 필드: risk_level, action_decision
    """
    rule_score = float(state.get("rule_score") or 0.0)
    ml_score = state.get("ml_score")  # None 가능 (모델 파일 없을 때)
    rule_hits = state.get("rule_hits") or []

    # ── 1. 명확한 고위험 → 즉시 block (LLM 불필요) ──────────
    if rule_score >= HIGH_RULE_THRESHOLD:
        return {"risk_level": "high", "action_decision": "block"}
    if ml_score is not None and ml_score >= HIGH_ML_THRESHOLD:
        return {"risk_level": "high", "action_decision": "block"}

    # ── 2. 명확한 저위험 → 즉시 approve (LLM 불필요) ────────
    ml_is_low = ml_score is None or ml_score <= LOW_ML_THRESHOLD
    if rule_score <= LOW_RULE_THRESHOLD and ml_is_low:
        return {"risk_level": "low", "action_decision": "approve"}

    # ── 3. 경계선 → GPT-4o에게 위임 ──────────────────────────
    return _llm_decision(state, rule_score, ml_score, rule_hits)


def _llm_decision(
    state: FraudState, rule_score: float, ml_score, rule_hits: list
) -> dict:
    """경계선 케이스에서 GPT-4o가 모든 신호를 종합해 판단한다."""

    # 판단에 필요한 정보를 프롬프트로 정리
    tx = state.get("tx_features") or {}
    cp = state.get("customer_profile") or {}
    mr = state.get("merchant_risk") or {}

    ml_score_str = f"{ml_score:.2f}" if ml_score is not None else "데이터 없음"

    # RAG 근거 자료가 있으면 프롬프트에 포함
    rag_evidence = state.get("rag_evidence") or []
    rag_section = ""
    if rag_evidence:
        rag_items = "\n".join(
            f"  · [{e.get('source', '?')}] (유사도: {e.get('similarity', 0):.2f}) {e.get('snippet', '')[:120]}"
            for e in rag_evidence[:3]  # 최대 3개만 포함 (프롬프트 길이 제한)
        )
        rag_section = f"\n- 유사 사기 사례 (RAG 검색 결과):\n{rag_items}"

    prompt = f"""당신은 금융 사기 탐지 전문가입니다.
아래 거래 분석 결과를 바탕으로 최종 판단을 내려주세요.

[분석 결과 요약]
- 거래 금액: ${tx.get("amount", 0):.2f}
- 거래 시각: {tx.get("hour_of_day", "?")}시 ({tx.get("day_of_week", "?")})
- 가맹점 위험도: {mr.get("risk_level", "알 수 없음")}
- 고객 금액 Z-score: {cp.get("amount_z_score", 0):.2f}
- 룰 기반 점수: {rule_score}점 (발동 룰: {", ".join(rule_hits) if rule_hits else "없음"})
- ML 사기 확률: {ml_score_str}{rag_section}

[판단 기준]
- high + block: 여러 위험 신호가 겹치거나, 단일 신호라도 매우 강할 때
- medium + review: 일부 위험 신호가 있으나 확실하지 않을 때, 사람이 검토 필요
- low + approve: 위험 신호가 미미하고 정상 거래로 볼 수 있을 때

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이:
{{"risk_level": "high 또는 medium 또는 low", "action_decision": "block 또는 review 또는 approve"}}"""

    try:
        messages = [
            SystemMessage(
                content="당신은 금융 사기 탐지 시스템입니다. JSON만 응답합니다."
            ),
            HumanMessage(content=prompt),
        ]
        response = _llm.invoke(messages)

        # JSON 파싱
        import json

        content = response.content.strip()
        # 마크다운 코드블록이 포함된 경우 제거
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content.strip())

        return {
            "risk_level": result.get("risk_level", "medium"),
            "action_decision": result.get("action_decision", "review"),
        }

    except Exception:
        # LLM 호출 실패 시 안전한 기본값: 사람에게 검토 요청
        return {"risk_level": "medium", "action_decision": "review"}
