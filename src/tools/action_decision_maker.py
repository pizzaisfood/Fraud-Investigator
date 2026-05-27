import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.state import FraudState

# ── 판단 기준 임계값 ────────────────────────────────────────────────
# 이 값들을 바꾸면 전체 시스템의 민감도가 바뀐다.
HIGH_RULE_THRESHOLD = 60      # 룰 점수 60 이상 → 명확한 고위험
HIGH_ML_THRESHOLD = 0.80      # ML 확률 80% 이상 → 명확한 고위험
ELEVATED_RULE_THRESHOLD = 45  # 룰+ML 둘 다 중상위 → 준고위험 (PM 결정 보완)
ELEVATED_ML_THRESHOLD = 0.60  # 룰 45 이상 + ML 0.60 이상이면 함께 고위험으로 확정
LOW_RULE_THRESHOLD = 20       # 룰 점수 20 이하
LOW_ML_THRESHOLD = 0.30       # ML 확률 30% 이하 → 둘 다 낮으면 저위험


def action_decision_maker(state: FraudState) -> dict:
    """
    Tool 7: Action Decision Maker
    - 역할: rule_score + ml_score를 종합해 최종 위험 등급과 조치를 결정한다.
    - LLM 사용: X (deterministic 룰만 사용 — PM 결정으로 LLM 판단 제거)
    - 읽는 State 필드: rule_score, ml_score
    - 쓰는 State 필드: risk_level, action_decision
    - 참고: LLM은 Tool 8(report_generator)에서 설명 역할만 수행
    """
    rule_score = float(state.get("rule_score") or 0.0)
    ml_score = state.get("ml_score")  # None 가능 (모델 파일 없을 때)

    # ── 1. 명확한 고위험 → 즉시 block ────────────────────────
    # 단일 신호만으로도 충분히 강할 때
    if rule_score >= HIGH_RULE_THRESHOLD:
        return {"risk_level": "high", "action_decision": "block"}
    if ml_score is not None and ml_score >= HIGH_ML_THRESHOLD:
        return {"risk_level": "high", "action_decision": "block"}

    # ── 1.5. 준고위험 → block ─────────────────────────────────
    # 룰과 ML이 둘 다 중상위권에서 겹칠 때
    # 왜 필요한가: "모든 경계선 = medium/review" 처리 시
    # 룰 55점 + ML 0.75 같은 강한 신호를 버리게 되는 문제를 방지
    if (
        rule_score >= ELEVATED_RULE_THRESHOLD
        and ml_score is not None
        and ml_score >= ELEVATED_ML_THRESHOLD
    ):
        return {"risk_level": "high", "action_decision": "block"}

    # ── 2. 명확한 저위험 → 즉시 approve ──────────────────────
    ml_is_low = ml_score is None or ml_score <= LOW_ML_THRESHOLD
    if rule_score <= LOW_RULE_THRESHOLD and ml_is_low:
        return {"risk_level": "low", "action_decision": "approve"}

    # ── 3. 경계선 → medium/review 고정 ────────────────────────
    # PM 결정 (2025-05): LLM은 최종 등급을 결정하지 않는다.
    # 이유: 금융 사기 탐지에서 "같은 입력 → 같은 출력" 재현성이
    #       LLM 정밀도보다 중요 (감사·규정 준수).
    # LLM의 역할: Tool 8(report_generator)에서
    #   "왜 이 거래가 사람의 검토가 필요한가"를 설명하는 것.
    return {"risk_level": "medium", "action_decision": "review"}


