import os
import sys
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.state import FraudState

load_dotenv()

_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    openai_api_key=os.environ.get("GENAI_TEAM09"),
)

_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError)


@retry(
    retry=retry_if_exception_type(_RETRYABLE_ERRORS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _invoke_with_retry(messages: list) -> str:
    response = _llm.invoke(messages)
    return response.content


def report_generator(state: FraudState) -> dict:
    """
    Tool 8: Report Generator
    - 읽는 State 필드: 기존 + rag_evidence
    - 쓰는 State 필드: report
    """
    base_prompt = _build_prompt(state)
    rag_section = _build_rag_section(state.get("rag_evidence"))
    enhanced_prompt = f"{base_prompt}\n\n{rag_section}" if rag_section else base_prompt

    messages = [
        SystemMessage(content=_get_enhanced_system_prompt()),
        HumanMessage(content=enhanced_prompt),
    ]

    try:
        content = _invoke_with_retry(messages)
        return {"report": content}
    except Exception as e:
        return {"report": f"[리포트 생성 실패: {e}]"}


def _get_enhanced_system_prompt() -> str:
    return """당신은 금융 사기 조사 전문가입니다.

### RAG 참고 자료 활용 원칙:
1. **역할 명확화**: RAG 자료는 최종 판단 근거가 아니라 "참고 정보"
2. **신뢰도 표시**: 모든 참고 자료에 유사도, 출처, 국내/해외 구분 명시
3. **표현 조심**:
   - 피하기: "증거", "판단 근거", "결정적"
   - 사용하기: "유사 사례 발견", "패턴 언급됨", "참고할 만함"
4. **국내/해외 구분**:
   - 해외 자료: "해외 지급결제 사기 보고서에서 유사한 패턴이 언급됨"
   - 국내 자료: "국내 사기 DB에서 동일 가맹점 관련 사례 발견"

### 리포트 구조:
1. 종합 판단 (Rule/ML 중심)
2. 주요 위험 지표
3. 정상/이상 요소 비교
4. [참고] 유사 사례 (rag_evidence 있을 시)
5. 권고 조치"""


def _build_rag_section(rag_evidence: Optional[List[Dict]]) -> str:
    if not rag_evidence:
        return ""

    sections = []
    sections.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    sections.append("[참고] 유사 사례 및 동향")
    sections.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    for i, evidence in enumerate(rag_evidence, 1):
        source = evidence.get("source", "알 수 없음")
        snippet = evidence.get("snippet", "")
        similarity = evidence.get("similarity", 0)
        tags = evidence.get("tags", [])
        source_label = "【국내】" if "내부" in source or "DB" in source else "【해외】"

        sections.append(
            f"""【{i}】 {source_label} {source}
  • 유사도: {similarity:.0%}
  • 태그: {', '.join(tags) if tags else "미분류"}
  • 내용: {snippet}

"""
        )

    sections.append(
        "※ 위 참고 자료는 조사 판단을 돕기 위한 정보입니다. "
        "최종 판단은 Rule/ML 점수와 전문가 검토에 따릅니다."
    )
    return "\n".join(sections)


def _build_prompt(state: FraudState) -> str:
    tx = state.get("tx_features") or {}
    cp = state.get("customer_profile") or {}
    mr = state.get("merchant_risk") or {}
    vs = state.get("velocity_signals") or {}

    rule_hits = state.get("rule_hits") or []
    rule_score = state.get("rule_score") or 0.0
    ml_score = state.get("ml_score")
    risk_level = state.get("risk_level") or "unknown"
    action = state.get("action_decision") or "unknown"
    rag_evidence = state.get("rag_evidence") or []

    ml_str = f"{ml_score * 100:.1f}%" if ml_score is not None else "분석 불가 (모델 없음)"

    v_mode = vs.get("mode", "unknown")
    if v_mode == "history":
        velocity_str = (
            f"1시간 내 {vs.get('txn_last_1h')}건 / "
            f"24시간 내 {vs.get('txn_last_24h')}건 / "
            f"일평균 {vs.get('avg_daily_txn_count')}건"
        )
    else:
        velocity_str = f"거래 이력 없음 (일평균 추정: {vs.get('avg_daily_txn_count')}건)"

    rule_hits_str = ", ".join(rule_hits) if rule_hits else "없음"

    action_map = {"block": "차단", "review": "검토 요청", "approve": "승인"}
    risk_map = {"high": "고위험", "medium": "중간", "low": "저위험"}
    action_ko = action_map.get(action, action)
    risk_ko = risk_map.get(risk_level, risk_level)

    if rag_evidence:
        rag_lines = "\n".join(
            f"  - [{e.get('source', '?')}] (유사도: {e.get('similarity', 0):.2f})\n"
            f" {e.get('snippet', '')}"
            for e in rag_evidence
        )
        rag_section = f"\n[7. 유사 사기 사례 (RAG 검색)]\n{rag_lines}"
    else:
        rag_section = "\n[7. 유사 사기 사례]\n- 검색 결과 없음 (RAG 미연동 또는 유사 사례 없음)"

    prompt = f"""다음은 거래 #{tx.get("trans_num", "N/A")}에 대한 사기 탐지 분석 결과입니다.
이 데이터를 바탕으로 전문적인 사기 조사 리포트를 작성해 주세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1. 거래 기본 정보]
- 카드 번호: {tx.get("cc_num", "N/A")}
- 거래 금액: ${tx.get("amount", 0):.2f} ({tx.get("amount_category", "N/A")})
- 거래 시각: {tx.get("hour_of_day", "?")}시 {tx.get("day_of_week", "?")} ({"새벽/야간" if tx.get("is_night_transaction") else "일반 시간대"})
- 가맹점: {tx.get("merchant", "N/A")} ({tx.get("category", "N/A")})
- 거래 지역: {tx.get("city", "N/A")}, {tx.get("state", "N/A")}

[2. 고객 프로필 비교]
- 30일 평균 거래금액: ${cp.get("avg_amount_30d", 0):.2f}
- 이번 거래 Z-score: {cp.get("amount_z_score", 0):.2f} ({"이상 금액" if cp.get("is_amount_anomalous") else "정상 범위"})
- 평소 이용 카테고리: {cp.get("usual_categories", [])}
- 이번 거래 카테고리 이상 여부: {"예" if cp.get("is_unusual_category") else "아니오"}
- 이번 거래 지역 이상 여부: {"예" if cp.get("is_unusual_city") else "아니오"}
- 신용 한도: ${cp.get("credit_limit", 0):.2f}

[3. 가맹점 위험도]
- DB 등록 여부: {"등록됨" if mr.get("found_in_db") else "미등록"}
- 위험 등급: {mr.get("risk_level", "N/A")}
- 사기 신고 건수: {mr.get("fraud_report_count", 0)}건
- 차지백 비율: {mr.get("chargeback_rate", 0) * 100:.1f}%

[4. 거래 빈도 분석 (Velocity)]
- {velocity_str}
- 비정상 빈도 감지: {"예" if vs.get("velocity_flag") else "아니오"}

[5. 룰 기반 스코어링]
- 발동된 룰: {rule_hits_str}
- 누적 위험 점수: {rule_score}점

[6. ML 모델 예측]
- 사기 확률: {ml_str}
{rag_section}

[8. 최종 판단]
- 위험 등급: {risk_ko} ({risk_level})
- 조치: {action_ko} ({action})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 데이터를 바탕으로 아래 구조로 리포트를 작성해 주세요:

## 사기 조사 리포트

### 1. 종합 판단
(한 문단: 이 거래가 왜 {risk_ko}으로 판단됐는지 핵심 근거 요약)

### 2. 주요 위험 지표
(발동된 룰과 ML 점수를 설명 — 수치의 의미를 해석해서 서술)

### 3. 정상/이상 요소 비교
(위험 신호 vs. 정상 신호를 균형 있게 제시)

### 4. 권고 조치
('{action_ko}'을 권고하는 이유와 다음 단계 제안)"""

    return prompt
