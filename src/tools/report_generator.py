import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.state import FraudState

load_dotenv()

_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
# temperature=0.3: 판단(Tool 7)보다는 약간 높게 → 자연스러운 문장 생성


def report_generator(state: FraudState) -> dict:
    """
    Tool 8: Report Generator
    - 역할: 모든 분석 결과를 종합해 자연어 조사 리포트를 생성한다.
    - LLM 사용: O (GPT-4o로 자연어 리포트 작성)
    - 읽는 State 필드: 전체 (transaction ~ action_decision)
    - 쓰는 State 필드: report
    """
    prompt = _build_prompt(state)

    try:
        messages = [
            SystemMessage(
                content=(
                    "당신은 금융 사기 조사 전문가입니다. "
                    "분석 데이터를 바탕으로 명확하고 전문적인 한국어 조사 리포트를 작성합니다."
                )
            ),
            HumanMessage(content=prompt),
        ]
        response = _llm.invoke(messages)
        return {"report": response.content}

    except Exception as e:
        return {"report": f"[리포트 생성 실패: {e}]"}


def _build_prompt(state: FraudState) -> str:
    """
    State의 모든 분석 결과를 프롬프트 텍스트로 조립한다.
    각 Tool의 결과를 읽어 GPT-4o가 이해하기 쉬운 형태로 정리한다.
    """
    tx = state.get("tx_features") or {}
    cp = state.get("customer_profile") or {}
    mr = state.get("merchant_risk") or {}
    vs = state.get("velocity_signals") or {}

    rule_hits = state.get("rule_hits") or []
    rule_score = state.get("rule_score") or 0.0
    ml_score = state.get("ml_score")
    risk_level = state.get("risk_level") or "unknown"
    action = state.get("action_decision") or "unknown"

    # ml_score 표시 처리
    ml_str = (
        f"{ml_score * 100:.1f}%" if ml_score is not None else "분석 불가 (모델 없음)"
    )

    # velocity 표시 처리
    v_mode = vs.get("mode", "unknown")
    if v_mode == "history":
        velocity_str = (
            f"1시간 내 {vs.get('txn_last_1h')}건 / "
            f"24시간 내 {vs.get('txn_last_24h')}건 / "
            f"일평균 {vs.get('avg_daily_txn_count')}건"
        )
    else:
        velocity_str = (
            f"거래 이력 없음 (일평균 추정: {vs.get('avg_daily_txn_count')}건)"
        )

    # 발동 룰이 없으면 "없음" 표시
    rule_hits_str = ", ".join(rule_hits) if rule_hits else "없음"

    # 최종 판단 한국어 변환
    action_map = {"block": "차단", "review": "검토 요청", "approve": "승인"}
    risk_map = {"high": "고위험", "medium": "중간", "low": "저위험"}
    action_ko = action_map.get(action, action)
    risk_ko = risk_map.get(risk_level, risk_level)

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

[7. 최종 판단]
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
