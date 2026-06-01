"""
schemas.py — 외부 팀과의 입출력 인터페이스 정의

이 파일이 하는 일:
    외부 팀(BE, RAG, ML)이 우리 파이프라인과 주고받는
    데이터 형식을 Pydantic으로 정의한다.

왜 Pydantic인가:
    - 잘못된 형식이 들어오면 파이프라인 시작 전에 바로 에러 발생
    - 에러 메시지가 친절함 (어떤 필드가 왜 잘못됐는지 알려줌)
    - FastAPI와 완벽 호환 → BE 팀이 그대로 붙여쓸 수 있음
"""

from pydantic import BaseModel, Field
from typing import Optional


# ══════════════════════════════════════════════════════════════════════
# 입력 스키마 — BE 팀이 우리 파이프라인에 보내는 데이터 형식
# ══════════════════════════════════════════════════════════════════════

class TransactionInput(BaseModel):
    """
    거래 1건을 표현하는 입력 스키마.

    BE 팀은 이 형식으로만 데이터를 보내면 된다.
    형식이 틀리면 파이프라인 시작 전에 자동으로 에러가 발생한다.

    사용 예시:
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
    """

    trans_num: str = Field(..., description="거래 고유 번호 (예: TXN-001)")
    # Field(...)에서 ...은 "이 필드는 반드시 있어야 한다"는 뜻 (필수값)

    trans_date_trans_time: str = Field(
        ..., description="거래 발생 시각 (형식: YYYY-MM-DD HH:MM:SS)"
    )

    cc_num: int = Field(..., description="카드 번호")

    merchant: str = Field(..., description="가맹점 이름")

    amt: float = Field(..., gt=0, description="거래 금액 (0보다 커야 함)")
    # gt=0: greater than 0. 음수나 0이 오면 자동으로 에러 발생

    category: str = Field(..., description="거래 카테고리 (예: shopping_net, grocery_pos)")

    city: str = Field(..., description="거래 발생 도시")

    state: str = Field(..., description="거래 발생 국가/주 (예: KR, CA)")


# ══════════════════════════════════════════════════════════════════════
# 출력 스키마 — 우리 파이프라인이 BE 팀에게 돌려주는 결과 형식
# ══════════════════════════════════════════════════════════════════════

class FraudInvestigationResult(BaseModel):
    """
    사기 조사 결과를 담는 출력 스키마.

    BE 팀은 이 형식으로 결과를 받아서 프론트엔드에 전달한다.

    사용 예시:
        result.risk_level       → "high" | "medium" | "low"
        result.action_decision  → "block" | "review" | "approve"
        result.report           → "## 사기 조사 리포트\n..."
    """

    # ── 핵심 판단 결과 ──────────────────────────────────────────────
    risk_level: str = Field(
        ..., description="위험 등급 (high | medium | low)"
    )
    action_decision: str = Field(
        ..., description="권고 조치 (block | review | approve)"
    )
    report: str = Field(
        ..., description="자연어 사기 조사 리포트 (마크다운 형식)"
    )

    # ── 상세 분석 결과 (디버깅 및 프론트 표시용) ──────────────────
    rule_hits: list[str] = Field(
        default=[], description="발동된 룰 ID 목록 (예: ['R001', 'R002'])"
    )
    rule_score: float = Field(
        default=0.0, description="룰 기반 누적 위험 점수"
    )
    ml_score: Optional[float] = Field(
        default=None,
        description="ML 모델 사기 확률 (0.0~1.0). 모델 없으면 None"
    )
    # Optional[float]: float일 수도 있고, None일 수도 있다는 뜻
    # 모델 파일(fraud_model.pkl)이 없을 때는 None이 들어온다
