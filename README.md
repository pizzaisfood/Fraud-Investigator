# 🔍 FraudInvestigator — LLM 기반 사기 거래 조사 에이전트

LangGraph를 활용한 8단계 파이프라인으로 신용카드 거래의 사기 여부를 분석하고,  
자연어 조사 리포트를 자동으로 생성하는 LLM 에이전트입니다.

---

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 과목 | LLM 응용 수업 팀 프로젝트 (6주) |
| 역할 | 팀장 · LLM 파이프라인 · 발표 |
| 목표 | 거래 데이터를 입력받아 사기 여부 판단 + 자연어 리포트 생성 |

---

## 🏗️ 아키텍처

```
입력: 거래 데이터 (JSON)
         ↓
[Tool 1] Transaction Analyzer     → 거래 특징 추출 (시각, 금액 카테고리 등)
         ↓
[Tool 2] Customer Profile Tool    → 고객 평소 패턴 조회 (Z-score 계산)
         ↓
[Tool 3] Merchant Risk Assessor   → 가맹점 위험도 조회 (차지백 비율 등)
         ↓
[Tool 4] Velocity Checker         → 단시간 다중 거래 감지
         ↓
[Tool 5] Rule-based Scorer        → FDS 룰 R001~R007 평가 · 점수 산출
         ↓
[Tool 6] ML Fraud Scorer          → LightGBM 사기 확률 예측 (0.0~1.0)
         ↓
[Tool 7] Action Decision Maker    → 최종 위험 등급 · 조치 결정 (Gemini)
         ↓
[Tool 8] Report Generator         → 자연어 조사 리포트 생성 (Gemini)
         ↓
출력: risk_level · action_decision · report
```

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| LLM 오케스트레이션 | LangGraph, LangChain |
| LLM 모델 | Google Gemini 2.5 Flash |
| ML 모델 | LightGBM |
| 프론트 | Streamlit |
| 언어 | Python 3.10+ |

---

## 📁 폴더 구조

```
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
├── services/
│   └── investigate.py              # graph 호출 래핑
├── frontend/
│   └── app.py                      # streamlit
├── scripts/
│   └── smoke_test.py
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

---

## ⚙️ 설치 및 실행

### 1. 레포지토리 클론

```bash
git clone https://github.com/Jeonghun-LEE-KMU/Fraud-Investigator.git
cd Fraud-Investigator
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
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

데모 UI / 로컬 테스트

```bash
python scripts/smoke_test.py
streamlit run frontend/app.py
```

UI 쪽에서는 `services/investigate.py` 의 `investigate(transaction)` 쓰면 됨

### Python에서 직접 실행

```python
from src.graph import fraud_graph

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

## 🔒 보안 주의사항

- `.env` 파일은 **절대 GitHub에 올리지 마세요** (`.gitignore`에 포함됨)
- `data/` 폴더의 CSV 파일도 gitignore 처리되어 있습니다

---

## 👥 팀 구성

| 역할 | 담당 |
|------|------|
| LLM 파이프라인 · 팀장 · 발표 | 이정훈 |
| RAG | - |
| PM · LLM-RAG 연결 | - |
| 백엔드 · 프론트엔드 | - |
| ML 모델 (LightGBM) | - |
