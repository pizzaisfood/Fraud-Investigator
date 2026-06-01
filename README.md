# FraudInvestigator

Rule/ML 기반 카드 이상거래 판단 결과를 LangGraph 파이프라인으로 정리하고, GPT-4o가 조사 담당자용 자연어 리포트를 생성하는 LLM 응용 수업 팀 프로젝트입니다.

핵심 방향은 **"Rule/ML 기반 판단 + LLM 리포트 생성"**입니다. LLM이 사기 여부를 직접 확정하지 않고, 이미 계산된 위험 신호를 사람이 검토하기 좋은 보고서로 설명합니다.

---

## 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 과목 | LLM 응용 수업 팀 프로젝트 |
| 프로젝트 | FraudInvestigator |
| 목표 | 거래 데이터 입력 → 위험 신호 분석 → 위험 등급/조치 결정 → 자연어 조사 리포트 생성 |
| 담당 | 이정훈: 팀장, LLM 파이프라인, 발표 |
| 최종 포지셔닝 | 사기 확정 자동화가 아니라 이상거래 조사 보조 Agent |

---

## 현재 구현 상태

- LangGraph 기반 8-Tool 파이프라인 구현
- **Tool 1~7 전부 LLM 미사용** — 규칙/계산/ML 기반으로만 동작 (완전 deterministic)
- **Tool 8만 GPT-4o** — 결과를 사람이 읽기 좋은 자연어 리포트로 변환 (설명 전담)
- Tool 8 GPT-4o 호출 실패 시 자동 재시도 (최대 3회, RateLimitError / APIConnectionError)
- LightGBM 모델 파일이 없으면 `ml_score=None`으로 계속 진행
- CSV 데이터가 없어도 기본값으로 계속 진행
- RAG 결과는 `rag_evidence` 필드로 받을 수 있도록 State 스키마 준비
- BE 팀용 단일 진입점 `investigate_transaction()` 제공
- 단위 테스트 31개 작성 (Tool 5·6·7 — 3개 파일)

---

## 아키텍처

```text
입력: 거래 데이터 JSON
  ↓
[Tool 1] transaction_analyzer
  - 거래 시각, 금액 카테고리, 야간 거래 여부 등 기본 특징 추출
  ↓
      ┌───────────────────────────────┐
      ↓                               ↓
[Tool 2] customer_profile_tool   [Tool 3] merchant_risk_assessor
  - 고객 평소 패턴 조회              - 가맹점 위험도 조회
  - Z-score 계산                     - 차지백 비율/신고 건수 확인
      ↓                               ↓
      └───────────────┬───────────────┘
                      ↓
        ┌─────────────────────────────┐
        ↓                             ↓
[Tool 4] velocity_checker      [Tool 6] ml_fraud_scorer
  - 단시간 다중 거래 감지            - LightGBM 사기 확률 예측
        ↓
[Tool 5] rule_based_scorer
  - FDS 룰 평가 및 rule_score 계산
        ↓                             ↓
        └───────────────┬─────────────┘
                        ↓
[Tool 7] action_decision_maker
  - rule_score + ml_score 기반 4-tier deterministic 판단 (LLM 없음)
  - high/block, medium/review, low/approve
                        ↓
[Tool 8] report_generator  ← 유일한 LLM 호출 지점
  - GPT-4o로 자연어 조사 리포트 생성 (재시도 최대 3회)
                        ↓
출력: risk_level, action_decision, report, rule_hits, rule_score, ml_score
```

### 결정 구조 — Tool 7은 왜 완전히 deterministic인가?

금융 이상거래 판단은 같은 입력에 대해 반드시 같은 결과가 나와야 합니다. 감사·규정 준수(audit) 환경에서는 "왜 이 거래를 막았는가"를 수치로 설명할 수 있어야 하기 때문입니다. LLM은 같은 프롬프트에도 확률적으로 다른 출력을 낼 수 있어, 결정 레이어에 넣으면 재현성이 깨집니다.

따라서 이 프로젝트는 역할을 명확히 분리합니다.

- **Tool 1~7: Deterministic layer** — 규칙/수치 계산/ML로 판단. 재현 가능, 설명 가능.
- **Tool 8: LLM layer** — GPT-4o가 이미 내려진 판단을 자연어로 설명. 결과를 바꾸지 않음.
- **Graceful Degradation**: 모델/CSV/RAG 파일이 없어도 파이프라인이 중단되지 않음.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| LLM 오케스트레이션 | LangGraph, LangChain |
| LLM 모델 | Google Gemini 2.5 Flash |
| ML 모델 | LightGBM |
| 백엔드 | FastAPI |
| 프론트엔드 | Streamlit |
| 언어 | Python 3.10+ |

---

## 폴더 구조

```text
FraudInvestigator/
├── src/
│   ├── state.py                    # LangGraph 공유 상태 스키마 (FraudState)
│   ├── graph.py                    # LangGraph 그래프 정의 및 컴파일
│   └── tools/
│       ├── transaction_analyzer.py   # Tool 1: 거래 특징 추출
│       ├── customer_profile_tool.py  # Tool 2: 고객 프로필 조회
│       ├── merchant_risk_assessor.py # Tool 3: 가맹점 위험도 조회
│       ├── velocity_checker.py       # Tool 4: 거래 빈도 분석
│       ├── rule_based_scorer.py      # Tool 5: 룰 기반 스코어링
│       ├── ml_fraud_scorer.py        # Tool 6: ML 모델 예측
│       ├── action_decision_maker.py  # Tool 7: 최종 판단 (LLM)
│       └── report_generator.py       # Tool 8: 자연어 리포트 생성 (LLM)
├── api/
│   └── main.py                     # FastAPI 엔드포인트
├── frontend/
│   └── app.py                      # Streamlit UI
├── data/                           # 데이터 파일 (gitignore 처리)
│   ├── customer_profiles.csv
│   ├── merchant_risk.csv
│   ├── fds_rules.csv
│   └── fraud_model.pkl
├── .env                            # API 키 (gitignore 처리, 공유 금지)
├── .gitignore
├── requirements.txt
└── README.md
```

`data/` 폴더는 Git에 올리지 않습니다. CSV와 모델 파일은 팀 공유 드라이브 등 별도 경로로 전달합니다.

---

## 설치

### 1. 가상환경 생성

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

### 4. 환경변수 설정

프로젝트 루트에 `.env` 파일 생성 후 아래 내용 입력:

```
GOOGLE_API_KEY=여기에_Google_AI_Studio_API_키_입력
```

> API 키 발급: [Google AI Studio](https://aistudio.google.com) → Get API Key

### 5. 데이터 파일 준비

`data/` 폴더에 아래 파일을 위치시킵니다 (Google Drive에서 다운로드):

- `customer_profiles.csv` — 고객 프로필 데이터
- `merchant_risk.csv` — 가맹점 위험도 데이터
- `fds_rules.csv` — FDS 룰 정의 (R001~R007)
- `fraud_model.pkl` — LightGBM 학습 모델 (ML 팀 제공)

---

## 🚀 사용 방법

### Python에서 직접 실행

```python
from src.api_interface import investigate_transaction
from src.schemas import TransactionInput

result = fraud_graph.invoke({
    "transaction": {
        "trans_num":              "abc123",
        "trans_date_trans_time":  "2020-06-21 03:14:25",
        "cc_num":                 123456789,
        "merchant":               "fraud_Shop_Name",
        "amt":                    1500.0,
        "category":               "shopping_net",
        "city":                   "Seoul",
        "state":                  "KR"
    }
})

print(result["action_decision"])  # "block" / "review" / "approve"
print(result["risk_level"])       # "high" / "medium" / "low"
print(result["report"])           # 자연어 조사 리포트
```

---

## BE 팀 연동

BE 팀은 내부 LangGraph 구조를 직접 알 필요 없이 `src.api_interface`만 호출하면 됩니다.

```python
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

print(result.risk_level)
print(result.action_decision)
print(result.report)
```

자세한 내용은 [docs/BE_INTERFACE.md](docs/BE_INTERFACE.md)를 참고하세요.

---

## RAG 연동 방향

현재 기준에서 RAG는 최종 위험 점수에 직접 반영하지 않습니다. 대신 유사 사기 사례를 `rag_evidence`로 전달하면 Tool 8 리포트 생성 단계에서 참고 근거로 사용합니다.

```python
rag_evidence = [
    {
        "source": "내부 사기 DB",
        "snippet": "동일 가맹점에서 새벽 시간대 고액 거래가 반복 탐지됨.",
        "similarity": 0.87,
        "tags": ["merchant_risk", "night_transaction"],
    }
]
```

RAG가 없거나 실패하면 `None`으로 두고 파이프라인을 계속 진행합니다.

---

## Action Decision 기준

현재 조치 값은 세 가지입니다.

| risk_level | action_decision | 의미 |
|---|---|---|
| `high` | `block` | 고위험. 차단 권고 |
| `medium` | `review` | 경계선. 사람 검토 권고 |
| `low` | `approve` | 저위험. 승인 권고 |

판단 기준은 [src/tools/action_decision_maker.py](src/tools/action_decision_maker.py)에 고정되어 있습니다.

- `rule_score >= 60`이면 고위험
- `ml_score >= 0.80`이면 고위험
- `rule_score >= 45`이고 `ml_score >= 0.60`이면 준고위험으로 고위험 처리
- `rule_score <= 20`이고 `ml_score <= 0.30` 또는 모델 없음이면 저위험
- 나머지는 중간위험 검토

---

## 보안 주의사항

- `.env`는 절대 GitHub에 올리지 않습니다.
- API 키를 `.txt`, `.py`, `.md` 파일에 직접 적지 않습니다.
- `data/`의 CSV, pkl, model 파일은 Git에 올리지 않습니다.
- 발표용으로 공유할 때는 스크린샷과 HTML에 API 키가 노출되지 않는지 확인합니다.

---

## 참고 문서

- [docs/BE_INTERFACE.md](docs/BE_INTERFACE.md): BE 팀 연동 가이드
- [docs/ML_INTERFACE.md](docs/ML_INTERFACE.md): ML 모델 피처 명세
- [docs/RAG_INTERFACE.md](docs/RAG_INTERFACE.md): RAG 연결 가이드
- [test_pipeline.py](test_pipeline.py): 3개 테스트 케이스 실행 스크립트
- [make_report.py](make_report.py): 발표용 HTML 리포트 생성 스크립트

---

## 팀 역할

| 역할 | 담당 |
|------|------|
| LLM 파이프라인 · 팀장 · 발표 | 이정훈 |
| RAG | - |
| PM · LLM-RAG 연결 | 채주형 |
| 백엔드 · 프론트엔드 | - |
| ML 모델 (LightGBM) | - |
