"""
schemas.py — 외부 팀과의 입출력 인터페이스 정의

이 파일이 하는 일:
    외부 팀(BE, RAG, ML)이 우리 파이프라인과 주고받는
    데이터 형식을 Pydantic으로 정의한다.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionInput(BaseModel):
    """
    거래 1건을 표현하는 입력 스키마.
    """

    model_config = ConfigDict(extra="allow")

    trans_num: str = Field(..., description="거래 고유 번호 (예: TXN-001)")
    trans_date_trans_time: str = Field(
        ..., description="거래 발생 시각 (형식: YYYY-MM-DD HH:MM:SS)"
    )
    cc_num: int = Field(..., description="카드 번호")
    merchant: str = Field(..., description="가맹점 이름")
    amt: float = Field(..., gt=0, description="거래 금액 (0보다 커야 함)")
    category: str = Field(
        ..., description="거래 카테고리 (예: shopping_net, grocery_pos)"
    )
    city: str = Field(..., description="거래 발생 도시")
    state: str = Field(..., description="거래 발생 국가/주 (예: KR, CA)")


class FraudInvestigationResult(BaseModel):
    """
    사기 조사 결과를 담는 출력 스키마.
    """

    model_config = ConfigDict(extra="allow")

    risk_level: str = Field(..., description="위험 등급 (high | medium | low)")
    action_decision: str = Field(
        ..., description="권고 조치 (block | review | approve)"
    )
    report: str = Field(..., description="자연어 사기 조사 리포트 (마크다운 형식)")
    rule_hits: List[str] = Field(
        default_factory=list, description="발동된 룰 ID 목록"
    )
    rule_score: float = Field(default=0.0, description="룰 기반 누적 위험 점수")
    ml_score: Optional[float] = Field(
        default=None, description="ML 모델 사기 확률 (0.0~1.0). 모델 없으면 None"
    )


class InvestigationTraceStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    status: str
    step: int
    total_steps: int
    focus_key: str
    updates: Dict[str, Any] = Field(default_factory=dict)
    focus_data: Optional[Any] = None


class FraudInvestigationRecord(BaseModel):
    """
    프론트 시각화용 상세 실행 기록 스키마.
    """

    model_config = ConfigDict(extra="allow")

    request_id: str
    created_at: str
    status: str
    transaction: Dict[str, Any]
    result: FraudInvestigationResult
    node_traces: List[InvestigationTraceStep] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
