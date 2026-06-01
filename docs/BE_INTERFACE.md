# BE 팀 인터페이스 가이드

> LLM 파이프라인(LangGraph)과 연결하는 방법을 설명합니다.  
> **내부 코드를 볼 필요 없습니다. 이 문서만 보면 됩니다.**

---

## 진입점

```python
from src.api_interface import investigate_transaction
from src.schemas import TransactionInput
```

함수 하나만 알면 됩니다: `investigate_transaction(tx) → FraudInvestigationResult`

---

## 입력: TransactionInput

| 필드 | 타입 | 필수 | 설명 | 예시 |
|---|---|---|---|---|
| `trans_num` | `str` | ✅ | 거래 고유 번호 | `"TXN-20240315-001"` |
| `trans_date_trans_time` | `str` | ✅ | 거래 시각 (YYYY-MM-DD HH:MM:SS) | `"2024-03-15 02:47:33"` |
| `cc_num` | `int` | ✅ | 카드 번호 | `1234567890123456` |
| `merchant` | `str` | ✅ | 가맹점 이름 | `"fraud_Legit_Shopping"` |
| `amt` | `float` | ✅ | 거래 금액 (0 초과) | `1850.00` |
| `category` | `str` | ✅ | 거래 카테고리 | `"shopping_net"` |
| `city` | `str` | ✅ | 거래 발생 도시 | `"Seoul"` |
| `state` | `str` | ✅ | 거래 발생 국가/주 | `"KR"` |

> **주의**: `amt`는 0 이하면 자동으로 ValidationError 발생합니다. 사전 필터링 불필요.

---

## 출력: FraudInvestigationResult

| 필드 | 타입 | 설명 | 가능한 값 |
|---|---|---|---|
| `risk_level` | `str` | 위험 등급 | `"high"` / `"medium"` / `"low"` |
| `action_decision` | `str` | 권고 조치 | `"block"` / `"review"` / `"approve"` |
| `report` | `str` | 자연어 조사 리포트 (마크다운) | — |
| `rule_hits` | `list[str]` | 발동된 룰 ID 목록 | `["R001", "R004"]` / `[]` |
| `rule_score` | `float` | 룰 기반 누적 점수 (발동된 룰 점수 합산) | `0.0` 이상 |
| `ml_score` | `float \| None` | ML 사기 확률 | `0.0` ~ `1.0` / `None` |

> **주의**: `ml_score`는 모델 파일(`data/fraud_model.pkl`)이 없으면 `None`입니다.  
> 프론트에서 `null` 체크 후 "분석 불가"로 표시해 주세요.

---

## FastAPI 연동 예시

```python
from fastapi import FastAPI
from src.api_interface import investigate_transaction
from src.schemas import TransactionInput, FraudInvestigationResult

app = FastAPI()

@app.post("/investigate", response_model=FraudInvestigationResult)
def investigate(tx: TransactionInput) -> FraudInvestigationResult:
    return investigate_transaction(tx)
```

FastAPI가 `TransactionInput`을 자동으로 JSON 파싱하고, 반환값을 자동으로 JSON 직렬화합니다.

---

## 에러 케이스

| 상황 | 동작 |
|---|---|
| `amt <= 0` | Pydantic이 422 ValidationError 자동 발생 |
| 필수 필드 누락 | Pydantic이 422 ValidationError 자동 발생 |
| ML 모델 파일 없음 | `ml_score = None`으로 파이프라인 정상 진행 |
| GPT API 호출 실패 | `risk_level`·`action_decision`은 Tool 7 결과 그대로 유지, `report`만 `"[리포트 생성 실패: ...]"` (최대 3회 재시도 후) |

---

## 실행 환경 요건

- `.env` 파일에 `GENAI_TEAM09` (OpenAI API 키) 필요
- `pip install -r requirements.txt` 설치 완료
- Python 3.11+
