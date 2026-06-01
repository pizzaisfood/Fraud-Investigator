"""
api_interface.py — BE/FE 팀용 단일 진입점
"""

from typing import Any, Dict, Union

from services.investigate import investigate, investigate_with_trace
from src.schemas import (
    FraudInvestigationRecord,
    FraudInvestigationResult,
    TransactionInput,
)


def investigate_transaction(
    tx: Union[TransactionInput, Dict[str, Any]]
) -> FraudInvestigationResult:
    """거래 1건을 받아 사기 조사를 수행하고 결과를 반환한다."""

    validated = tx if isinstance(tx, TransactionInput) else TransactionInput.model_validate(tx)
    result = investigate(validated.model_dump())
    return FraudInvestigationResult.model_validate(result)


def investigate_transaction_with_trace(
    tx: Union[TransactionInput, Dict[str, Any]]
) -> FraudInvestigationRecord:
    """프론트 시각화용 상세 trace를 포함한 실행 기록을 반환한다."""

    validated = tx if isinstance(tx, TransactionInput) else TransactionInput.model_validate(tx)
    record = investigate_with_trace(validated.model_dump())
    return FraudInvestigationRecord.model_validate(record)
