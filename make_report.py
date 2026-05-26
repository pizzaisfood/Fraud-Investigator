"""
make_report.py — 테스트 결과를 HTML 카드 이미지로 저장

실행 방법:
    python make_report.py

결과:
    fraud_report.html 파일 생성 → 브라우저에서 자동으로 열림
    → 브라우저에서 Cmd+Shift+4 로 스크린샷 → 카톡 공유
"""

import sys, os, time, webbrowser
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.graph import fraud_graph

# ── 테스트 케이스 ────────────────────────────────────────────────────
TEST_CASES = [
    {
        "name": "고위험 거래",
        "desc": "새벽 2시 · $1,850 · 온라인쇼핑",
        "transaction": {
            "trans_num": "TEST-001",
            "trans_date_trans_time": "2024-03-15 02:47:33",
            "cc_num": 1234567890,
            "merchant": "fraud_Legit_Shopping",
            "amt": 1850.00,
            "category": "shopping_net",
            "city": "Seoul", "state": "KR",
        },
    },
    {
        "name": "저위험 거래",
        "desc": "낮 12시 · $42.50 · 식료품",
        "transaction": {
            "trans_num": "TEST-002",
            "trans_date_trans_time": "2024-03-15 12:30:00",
            "cc_num": 1234567890,
            "merchant": "grocery_store_mart",
            "amt": 42.50,
            "category": "grocery_pos",
            "city": "Seoul", "state": "KR",
        },
    },
    {
        "name": "경계선 거래",
        "desc": "저녁 7시 · $280 · 미용",
        "transaction": {
            "trans_num": "TEST-003",
            "trans_date_trans_time": "2024-03-15 19:15:00",
            "cc_num": 1234567890,
            "merchant": "beauty_salon_plus",
            "amt": 280.00,
            "category": "personal_care",
            "city": "Busan", "state": "KR",
        },
    },
]

# ── 파이프라인 실행 ──────────────────────────────────────────────────
print("🔍 파이프라인 실행 중...\n")
results = []
for case in TEST_CASES:
    print(f"   ⏳ {case['name']} 분석 중...")
    t = time.time()
    res = fraud_graph.invoke({"transaction": case["transaction"]})
    elapsed = time.time() - t
    results.append({"case": case, "result": res, "elapsed": elapsed})
    print(f"   ✅ 완료 ({elapsed:.1f}초)\n")

# ── HTML 생성 ────────────────────────────────────────────────────────
RISK_COLOR = {"high": "#FF4757", "medium": "#FFA502", "low": "#2ED573"}
RISK_BG    = {"high": "#FFF0F1", "medium": "#FFFBF0", "low": "#F0FFF4"}
RISK_LABEL = {"high": "🔴 고위험", "medium": "🟡 중간위험", "low": "🟢 저위험"}
ACTION_LABEL = {"block": "🚫 차단", "review": "🔍 검토 요청", "approve": "✅ 승인"}

def badge(text, color, bg):
    return f'<span style="background:{bg};color:{color};border:1.5px solid {color};border-radius:20px;padding:3px 12px;font-weight:700;font-size:13px;">{text}</span>'

def row(label, value, warn=False):
    color = "#FF4757" if warn else "#555"
    return f"""
        <tr>
          <td style="padding:6px 10px;color:#888;font-size:13px;width:110px;">{label}</td>
          <td style="padding:6px 10px;color:{color};font-size:13px;font-weight:{'600' if warn else '400'};">{value}</td>
        </tr>"""

cards_html = ""
for item in results:
    case   = item["case"]
    r      = item["result"]
    risk   = r.get("risk_level", "unknown")
    action = r.get("action_decision", "unknown")
    tx     = r.get("tx_features") or {}
    cp     = r.get("customer_profile") or {}
    mr     = r.get("merchant_risk") or {}
    vs     = r.get("velocity_signals") or {}
    rule_hits  = r.get("rule_hits") or []
    rule_score = r.get("rule_score") or 0.0
    ml_score   = r.get("ml_score")
    report     = r.get("report") or ""

    # 리포트 첫 단락만 추출
    report_lines = [l for l in report.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("**")]
    report_preview = report_lines[0][:200] + "..." if report_lines else "리포트 없음"

    c = RISK_COLOR.get(risk, "#888")
    bg = RISK_BG.get(risk, "#F9F9F9")

    cards_html += f"""
    <div style="background:white;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.08);
                margin-bottom:20px;overflow:hidden;border-top:5px solid {c};">

      <!-- 카드 헤더 -->
      <div style="padding:18px 22px 12px;border-bottom:1px solid #F0F0F0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-size:17px;font-weight:700;color:#1A1A2E;">{case['name']}</div>
            <div style="font-size:13px;color:#888;margin-top:2px;">{case['desc']}</div>
          </div>
          <div style="text-align:right;">
            {badge(RISK_LABEL.get(risk,'?'), c, bg)}
            <br><span style="font-size:12px;color:#888;margin-top:5px;display:block;">{ACTION_LABEL.get(action,'?')}</span>
          </div>
        </div>
      </div>

      <!-- 분석 결과 -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">

        <!-- 좌측 -->
        <div style="padding:14px 20px;border-right:1px solid #F5F5F5;">
          <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:1px;margin-bottom:8px;">ANALYSIS</div>
          <table style="width:100%;border-collapse:collapse;">
            {row("거래금액", f"${tx.get('amount',0):,.2f} ({tx.get('amount_category','?')})")}
            {row("거래시각", f"{tx.get('hour_of_day','?')}시 {'🌙야간' if tx.get('is_night_transaction') else '☀️주간'}", tx.get('is_night_transaction',False))}
            {row("Z-score", f"{cp.get('amount_z_score',0):.2f} {'⚠️이상' if cp.get('is_amount_anomalous') else '정상'}", cp.get('is_amount_anomalous',False))}
            {row("카테고리", f"{'⚠️비정상' if cp.get('is_unusual_category') else '정상'}", cp.get('is_unusual_category',False))}
            {row("거래지역", f"{'⚠️비정상' if cp.get('is_unusual_city') else '정상'}", bool(cp.get('is_unusual_city', False)))}
            {row("가맹점위험", f"{mr.get('risk_level','?')} {'⚠️' if mr.get('is_high_risk') else ''}", mr.get('is_high_risk',False))}
          </table>
        </div>

        <!-- 우측 -->
        <div style="padding:14px 20px;">
          <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:1px;margin-bottom:8px;">SCORING</div>
          <table style="width:100%;border-collapse:collapse;">
            {row("발동 룰", ', '.join(rule_hits) if rule_hits else '없음', bool(rule_hits))}
            {row("룰 점수", f"{rule_score}점", rule_score >= 30)}
            {row("ML 확률", f"{ml_score*100:.1f}%" if ml_score is not None else "모델 없음")}
            {row("빈도이상", '⚠️ 감지됨' if vs.get('velocity_flag') else '정상', vs.get('velocity_flag',False))}
            {row("실행시간", f"{item['elapsed']:.1f}초")}
          </table>
        </div>
      </div>

      <!-- LLM 리포트 미리보기 -->
      <div style="padding:12px 22px 16px;background:#FAFAFA;border-top:1px solid #F0F0F0;">
        <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:1px;margin-bottom:6px;">AI REPORT PREVIEW</div>
        <div style="font-size:13px;color:#444;line-height:1.6;font-style:italic;">
          "{report_preview}"
        </div>
      </div>
    </div>
    """

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FraudInvestigator — 테스트 리포트</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#F0F2F5;font-family:'Inter',sans-serif;">

  <div style="max-width:700px;margin:0 auto;padding:30px 20px 40px;">

    <!-- 헤더 -->
    <div style="text-align:center;margin-bottom:28px;">
      <div style="font-size:28px;font-weight:700;color:#1A1A2E;">🔍 FraudInvestigator</div>
      <div style="font-size:14px;color:#888;margin-top:6px;">LangGraph · GPT-4o · LightGBM</div>
      <div style="margin-top:14px;display:inline-flex;gap:10px;flex-wrap:wrap;justify-content:center;">
        <span style="background:#E8F5E9;color:#2E7D32;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;">✅ 8-Tool Pipeline</span>
        <span style="background:#E3F2FD;color:#1565C0;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;">🤖 LLM 자동 판단</span>
        <span style="background:#FFF3E0;color:#E65100;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;">📊 ML 통합 (예정)</span>
      </div>
    </div>

    <!-- 요약 테이블 -->
    <div style="background:white;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.08);
                padding:20px 24px;margin-bottom:24px;">
      <div style="font-size:15px;font-weight:700;color:#1A1A2E;margin-bottom:14px;">📋 테스트 결과 요약</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#F8F9FA;">
            <th style="padding:10px 12px;text-align:left;color:#555;font-weight:600;border-radius:8px 0 0 8px;">케이스</th>
            <th style="padding:10px 12px;text-align:center;color:#555;font-weight:600;">룰 점수</th>
            <th style="padding:10px 12px;text-align:center;color:#555;font-weight:600;">ML 확률</th>
            <th style="padding:10px 12px;text-align:center;color:#555;font-weight:600;">위험 등급</th>
            <th style="padding:10px 12px;text-align:center;color:#555;font-weight:600;border-radius:0 8px 8px 0;">조치</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f'''
          <tr style="border-top:1px solid #F0F0F0;">
            <td style="padding:10px 12px;font-weight:600;color:#333;">{item["case"]["name"]}</td>
            <td style="padding:10px 12px;text-align:center;color:#555;">{item["result"].get("rule_score",0)}점</td>
            <td style="padding:10px 12px;text-align:center;color:#555;">{"N/A" if item["result"].get("ml_score") is None else f"{item['result']['ml_score']*100:.0f}%"}</td>
            <td style="padding:10px 12px;text-align:center;">{badge(RISK_LABEL.get(item["result"].get("risk_level","?"),"?"), RISK_COLOR.get(item["result"].get("risk_level","?"),"#888"), RISK_BG.get(item["result"].get("risk_level","?"),"#F9F9F9"))}</td>
            <td style="padding:10px 12px;text-align:center;color:#555;">{ACTION_LABEL.get(item["result"].get("action_decision","?"),"?")}</td>
          </tr>''' for item in results)}
        </tbody>
      </table>
    </div>

    <!-- 상세 카드 -->
    {cards_html}

    <!-- 푸터 -->
    <div style="text-align:center;margin-top:10px;font-size:12px;color:#AAA;">
      LLM 응용 수업 팀 프로젝트 · 이정훈 · {time.strftime('%Y.%m.%d')}
    </div>
  </div>

</body>
</html>"""

# ── 파일 저장 & 브라우저 열기 ────────────────────────────────────────
output_path = Path(__file__).parent / "fraud_report.html"
output_path.write_text(html, encoding="utf-8")

print(f"✅ 리포트 저장 완료: {output_path}")
print("🌐 브라우저에서 자동으로 열립니다...\n")
print("📲 카톡 공유 방법:")
print("   1. 브라우저에서 리포트 확인")
print("   2. macOS: Cmd + Shift + 4  →  원하는 영역 드래그 → 스크린샷")
print("   3. 바탕화면의 스크린샷 파일 → 카톡으로 공유")

webbrowser.open(f"file://{output_path.resolve()}")
