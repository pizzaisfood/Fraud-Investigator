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
|---|---|
| Agent orchestration | LangGraph, LangChain |
| LLM | OpenAI GPT-4o |
| ML | LightGBM 모델 연동 준비, scikit-learn/joblib 호환 |
| 데이터 처리 | pandas |
| API 인터페이스 | Pydantic, FastAPI 연동 가능 구조 |
| 언어 | Python 3.11+ |

---

## 폴더 구조

```text
FraudInvestigator/
├── src/
│   ├── state.py                    # LangGraph 공유 State 스키마
│   ├── graph.py                    # StateGraph 구성 및 컴파일
│   ├── schemas.py                  # 외부 입출력 Pydantic 스키마
│   ├── api_interface.py            # BE 팀용 단일 진입점
│   └── tools/
│       ├── transaction_analyzer.py
│       ├── customer_profile_tool.py
│       ├── merchant_risk_assessor.py
│       ├── velocity_checker.py
│       ├── rule_based_scorer.py
│       ├── ml_fraud_scorer.py
│       ├── action_decision_maker.py
│       └── report_generator.py
├── docs/
│   ├── BE_INTERFACE.md             # BE 팀 연동 가이드
│   ├── ML_INTERFACE.md             # ML 모델 피처/파일 명세
│   └── RAG_INTERFACE.md            # RAG 결과 연결 가이드
├── tests/
│   ├── test_action_decision_maker.py   # Tool 7: 4-tier 판단 로직 (13개)
│   ├── test_rule_based_scorer.py       # Tool 5: 6개 룰 (R001, R002, R004~R007) 경계값 (18개)
│   └── test_ml_fraud_scorer.py         # Tool 6: Graceful Degradation (2개 + 2 skipped)
├── test_pipeline.py                # 3개 케이스 파이프라인 테스트
├── make_report.py                  # 발표용 HTML 리포트 생성
├── .env.example                    # 환경변수 설정 예시
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
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env.example`을 복사해서 `.env`로 이름을 바꾸고 실제 키를 채워 넣습니다.

```bash
cp .env.example .env
# .env 파일을 열어서 GENAI_TEAM09 값을 실제 키로 교체
```

```env
GENAI_TEAM09=sk-...your-openai-api-key-here...
```

`GENAI_TEAM09`가 없으면 GPT-4o 리포트 생성은 실패할 수 있지만, Rule/ML 판단 파이프라인 자체는 최대한 계속 진행되도록 설계되어 있습니다.

---

## 데이터 파일

아래 파일은 있으면 더 정확한 분석을 하고, 없어도 기본값으로 동작합니다.

```text
data/
├── customer_profiles.csv   # 고객 평소 거래 패턴
├── merchant_risk.csv       # 가맹점 위험도
├── fds_rules.csv           # FDS 룰 점수
└── fraud_model.pkl         # ML 팀이 학습한 LightGBM 모델
```

### ML 모델 피처

`fraud_model.pkl`은 다음 10개 피처 순서로 학습되어야 합니다.

1. `amt`
2. `amount_ratio`
3. `is_unusual_hour`
4. `is_unusual_city`
5. `is_unusual_category`
6. `merchant_risk_score`
7. `avg_amount_30d`
8. `std_amount_30d`
9. `chargeback_rate`
10. `fraud_report_count`

자세한 내용은 [docs/ML_INTERFACE.md](docs/ML_INTERFACE.md)를 참고하세요.

---

## 실행 방법

### 1. 전체 파이프라인 테스트

```bash
python test_pipeline.py
```

테스트 케이스는 3개입니다.

- Case 1: 고위험 거래
- Case 2: 저위험 거래
- Case 3: 경계선 거래

### 2. 발표용 HTML 리포트 생성

```bash
python make_report.py
```

`fraud_report.html` 파일이 생성됩니다. Streamlit/BE 연결이 불안정할 때 발표 백업 자료로 사용할 수 있습니다.

### 3. 단위 테스트

```bash
python -m pytest tests/ -v
```

현재 31개 테스트가 3개 파일에 걸쳐 작성되어 있습니다.

| 파일 | 대상 | 케이스 |
|------|------|--------|
| `test_action_decision_maker.py` | Tool 7 — 4-tier 판단 경계값 | 13개 |
| `test_rule_based_scorer.py` | Tool 5 — 6개 룰 (R001, R002, R004~R007) 발동 조건 | 18개 |
| `test_ml_fraud_scorer.py` | Tool 6 — 모델 없을 때 Graceful Degradation | 2개 + 2 skipped |

---

## Python 사용 예시

```python
from src.graph import fraud_graph

result = fraud_graph.invoke({
    "transaction": {
        "trans_num": "TEST-001",
        "trans_date_trans_time": "2024-03-15 02:47:33",
        "cc_num": 1234567890,
        "merchant": "fraud_Legit_Shopping",
        "amt": 1850.00,
        "category": "shopping_net",
        "city": "Seoul",
        "state": "KR",
    }
})

print(result["risk_level"])        # "high" | "medium" | "low"
print(result["action_decision"])   # "block" | "review" | "approve"
print(result["report"])            # GPT-4o 자연어 조사 리포트
print(result["rule_hits"])         # 발동된 FDS 룰 목록
print(result["ml_score"])          # 모델 없으면 None
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
|---|---|
| LLM 파이프라인, 팀장, 발표 | 이정훈 |
| ML 모델 | ML 담당 팀원 |
| RAG | RAG 담당 팀원 |
| PM, LLM-RAG 연결 | PM 담당 팀원 |
| BE/FE | BE/FE 담당 팀원 |
