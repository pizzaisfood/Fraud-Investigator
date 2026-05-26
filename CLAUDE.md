# CLAUDE.md — FraudInvestigator

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- **Notion**: https://www.notion.so/35dd359e3157816fb904e8702f80f35e
- **GitHub**: https://github.com/Jeonghun-LEE-KMU/Fraud-Investigator
- **성격**: LLM 응용 수업 팀 프로젝트 (6주) — 이정훈: 팀장 · LLM 파이프라인 전담 · 발표

---

## 실행 명령어

```bash
source .venv/bin/activate
python test_pipeline.py   # 3-케이스 파이프라인 테스트 (고위험/저위험/경계선)
python make_report.py     # HTML 리포트 생성 + 브라우저 자동 오픈
```

`.env`에 `GENAI_TEAM09` 필요 (OpenAI GPT-4o 사용).  
`data/` 폴더 파일 없어도 동작 — Graceful Degradation 설계.

---

## 아키텍처

8개 Tool이 **의존성 기반 병렬 실행**으로 연결된 LangGraph StateGraph. 모든 Tool은 `FraudState`를 공유 상태로 받아 해당 필드를 채운 dict를 반환한다.

```
입력 (transaction dict)
  → [1] transaction_analyzer            # 시각·금액 카테고리 추출
        ├──→ [2] customer_profile_tool  # CSV 조회 + Z-score 계산  ┐ 병렬
        └──→ [3] merchant_risk_assessor # 가맹점 위험도 조회        ┘
              ├──→ [4] velocity_checker   # 단시간 다중 거래 감지 ┐ 병렬
              │         → [5] rule_based_scorer # FDS 룰 R001~R007┘
              └──→ [6] ml_fraud_scorer   # LightGBM 사기 확률 예측
  → [7] action_decision_maker     # 최종 판단 (GPT-4o, 경계선 케이스만)
  → [8] report_generator          # 자연어 리포트 생성 (GPT-4o)
출력: risk_level · action_decision · report
```

**핵심 파일:**
- `src/state.py` — `FraudState` TypedDict (전체 파이프라인 공유 상태 스키마)
- `src/graph.py` — 그래프 빌드·컴파일, import 시 `fraud_graph` 싱글턴 생성
- `src/tools/*.py` — 각 Tool (시그니처: `def tool_name(state: FraudState) -> dict`)

**설계 원칙:**
- Tool 1~6은 규칙/ML 기반 (비용 최소화)
- Tool 7·8만 GPT-4o 호출 (LLM as tiebreaker + reporter)
- `fraud_graph = build_graph()`는 모듈 import 시 한 번만 실행 (Module-level 로딩)

---

## Tool 추가 방법

1. `src/tools/new_tool.py` 생성 — `def new_tool(state: FraudState) -> dict:` 형태
2. `src/state.py`의 `FraudState`에 출력 필드 추가 (`Optional[...]`)
3. `src/graph.py`에서 `add_node()` + `add_edge()` 등록

---

## 팀 구성 및 인터페이스

| 역할 | 담당 | 인터페이스 |
|------|------|-----------|
| LLM 파이프라인 · 팀장 | 이정훈 | `fraud_graph.invoke({"transaction": {...}})` |
| RAG 연동 | 팀원 | — |
| PM · LLM-RAG 연결 | 팀원 | — |
| 백엔드(FastAPI) · 프론트(Streamlit) | 팀원 | `api/main.py` |
| ML 모델(LightGBM) | 팀원 | `data/fraud_model.pkl` |

> **LLM**: GPT-4o 사용 (`GENAI_TEAM09` 환경변수). Tool 7(판단)은 경계선 케이스에서만 호출, Tool 8(리포트)은 항상 호출.
