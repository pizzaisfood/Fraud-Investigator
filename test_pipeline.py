"""
test_pipeline.py — FraudInvestigator 전체 파이프라인 테스트

실행 방법:
    python test_pipeline.py

테스트 케이스:
    Case 1 — 고위험 거래 (새벽 + 고액 + 온라인쇼핑)
    Case 2 — 저위험 거래 (낮 시간 + 소액 + 식료품)
    Case 3 — 경계선 거래 (저녁 + 중간 금액 + 미용)

주의:
    - data/ 폴더 CSV 없이도 실행 가능 (Graceful Degradation)
    - fraud_model.pkl 없이도 실행 가능 (ml_score = None)
    - GOOGLE_API_KEY가 .env에 있어야 Tool 7, 8이 동작함
"""

import sys
import os
import time

# ── 프로젝트 루트를 Python 경로에 추가 ──────────────────────────────
# 왜 필요한가?
#   "from src.graph import fraud_graph" 처럼 src 패키지를 import하려면
#   Python이 프로젝트 루트를 알아야 한다.
#   sys.path에 추가하면 어느 폴더에서 실행해도 import가 된다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.graph import fraud_graph


# ══════════════════════════════════════════════════════════════════════
# 테스트용 거래 데이터 정의
# ══════════════════════════════════════════════════════════════════════

TEST_CASES = [
    {
        "name": "Case 1 — 고위험 (새벽 + 고액 + 온라인쇼핑)",
        "transaction": {
            "trans_num":             "TEST-001",
            "trans_date_trans_time": "2024-03-15 02:47:33",   # 새벽 2시
            "cc_num":                1234567890,
            "merchant":              "fraud_Legit_Shopping",  # "fraud_" 접두사
            "amt":                   1850.00,                 # 고액
            "category":              "shopping_net",          # 온라인쇼핑
            "city":                  "Seoul",
            "state":                 "KR",
        },
    },
    {
        "name": "Case 2 — 저위험 (낮 시간 + 소액 + 식료품)",
        "transaction": {
            "trans_num":             "TEST-002",
            "trans_date_trans_time": "2024-03-15 12:30:00",   # 낮 12시
            "cc_num":                1234567890,
            "merchant":              "grocery_store_mart",
            "amt":                   42.50,                   # 소액
            "category":              "grocery_pos",           # 식료품
            "city":                  "Seoul",
            "state":                 "KR",
        },
    },
    {
        "name": "Case 3 — 경계선 (저녁 + 중간 금액 + 미용)",
        "transaction": {
            "trans_num":             "TEST-003",
            "trans_date_trans_time": "2024-03-15 19:15:00",   # 저녁 7시
            "cc_num":                1234567890,
            "merchant":              "beauty_salon_plus",
            "amt":                   280.00,                  # 중간 금액
            "category":              "personal_care",         # 미용
            "city":                  "Busan",
            "state":                 "KR",
        },
    },
]


# ══════════════════════════════════════════════════════════════════════
# 출력 헬퍼 함수
# ══════════════════════════════════════════════════════════════════════

def print_separator(char="═", width=60):
    """구분선 출력"""
    print(char * width)


def print_result(case_name: str, result: dict, elapsed: float):
    """
    테스트 결과를 보기 좋게 출력한다.

    result는 FraudState 전체 딕셔너리 —
    LangGraph는 invoke() 후 최종 State를 그대로 반환한다.
    """
    print_separator()
    print(f"  {case_name}")
    print_separator()

    # ── 핵심 판단 결과 ───────────────────────────────────────────
    risk    = result.get("risk_level", "N/A")
    action  = result.get("action_decision", "N/A")

    # 위험도별 이모지 (가독성 향상)
    risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk, "⚪")
    action_emoji = {"block": "🚫", "review": "🔍", "approve": "✅"}.get(action, "❓")

    print(f"\n  {risk_emoji}  위험 등급    : {risk.upper()}")
    print(f"  {action_emoji}  최종 조치    : {action.upper()}")

    # ── 중간 분석 결과 요약 ──────────────────────────────────────
    tx  = result.get("tx_features") or {}
    cp  = result.get("customer_profile") or {}
    mr  = result.get("merchant_risk") or {}
    vs  = result.get("velocity_signals") or {}

    print(f"\n  ── Tool 1 (거래 분석) ───────────────────────")
    print(f"     거래 금액  : ${tx.get('amount', 0):.2f}  [{tx.get('amount_category', '?')}]")
    print(f"     거래 시각  : {tx.get('hour_of_day', '?')}시  {'🌙 새벽/야간' if tx.get('is_night_transaction') else '☀️ 일반 시간대'}")
    print(f"     카테고리   : {tx.get('category', '?')}")

    print(f"\n  ── Tool 2 (고객 프로필) ─────────────────────")
    print(f"     Z-score    : {cp.get('amount_z_score', 0.0):.2f}  {'⚠️ 이상' if cp.get('is_amount_anomalous') else '정상'}")
    print(f"     카테고리   : {'⚠️ 비정상' if cp.get('is_unusual_category') else '정상'}")
    print(f"     거래지역   : {'⚠️ 비정상' if cp.get('is_unusual_city') else '정상'}")

    print(f"\n  ── Tool 3 (가맹점 위험도) ───────────────────")
    print(f"     위험 등급  : {mr.get('risk_level', '?')}  {'⚠️ 고위험' if mr.get('is_high_risk') else ''}")
    print(f"     차지백     : {mr.get('chargeback_rate', 0) * 100:.1f}%  {'⚠️ 높음' if mr.get('is_high_chargeback') else ''}")

    print(f"\n  ── Tool 4 (거래 빈도) ───────────────────────")
    print(f"     빈도 이상  : {'⚠️ 감지됨' if vs.get('velocity_flag') else '정상'}")
    print(f"     분석 모드  : {vs.get('mode', '?')}")

    rule_hits  = result.get("rule_hits") or []
    rule_score = result.get("rule_score") or 0.0
    ml_score   = result.get("ml_score")

    print(f"\n  ── Tool 5 (룰 스코어) ───────────────────────")
    print(f"     발동 룰    : {', '.join(rule_hits) if rule_hits else '없음'}")
    print(f"     누적 점수  : {rule_score}점")

    print(f"\n  ── Tool 6 (ML 예측) ─────────────────────────")
    if ml_score is not None:
        print(f"     사기 확률  : {ml_score * 100:.1f}%")
    else:
        print(f"     사기 확률  : 분석 불가 (model 없음 — 정상 동작)")

    # ── LLM 리포트 (처음 500자만 미리보기) ──────────────────────
    report = result.get("report") or ""
    print(f"\n  ── Tool 8 (자연어 리포트 미리보기) ──────────")
    if report.startswith("[리포트 생성 실패"):
        print(f"     {report}")
    else:
        preview = report[:500].replace("\n", "\n     ")
        print(f"     {preview}")
        if len(report) > 500:
            print(f"     ... (총 {len(report)}자)")

    print(f"\n  ⏱️  실행 시간: {elapsed:.2f}초\n")


# ══════════════════════════════════════════════════════════════════════
# 메인 실행
# ══════════════════════════════════════════════════════════════════════

def main():
    print_separator("═")
    print("  🔍  FraudInvestigator — 파이프라인 테스트")
    print_separator("═")
    print(f"  테스트 케이스 수: {len(TEST_CASES)}개\n")

    for i, case in enumerate(TEST_CASES, start=1):
        print(f"\n  [{i}/{len(TEST_CASES)}] '{case['name']}' 실행 중...")

        start_time = time.time()

        try:
            # ── fraud_graph.invoke() ────────────────────────────────
            # LangGraph는 초기 State(딕셔너리)를 받아
            # 8개 노드를 순서대로 실행하고 최종 State를 반환한다.
            result = fraud_graph.invoke({"transaction": case["transaction"]})
            elapsed = time.time() - start_time
            print_result(case["name"], result, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n  ❌ 오류 발생: {e}")
            print(f"  ⏱️  실행 시간: {elapsed:.2f}초\n")

    print_separator("═")
    print("  ✅  테스트 완료")
    print_separator("═")


if __name__ == "__main__":
    # __name__ == "__main__" 패턴:
    #   이 파일을 직접 실행할 때만 main()이 호출된다.
    #   다른 파일에서 import해도 자동 실행되지 않는다.
    main()
