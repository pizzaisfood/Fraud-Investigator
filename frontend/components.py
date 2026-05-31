import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from typing import Optional

from services.investigate import NODE_DEFINITIONS, sample_transaction


def build_transaction_form():
    sample = sample_transaction()
    st.caption("기본 샘플값을 수정해서 분석 요청을 생성할 수 있습니다.")
    sample_dt = datetime.strptime(sample["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S")

    col1, col2 = st.columns(2)
    with col1:
        trans_num = st.text_input("거래번호", sample["trans_num"])
        trans_date = st.date_input("거래일", value=sample_dt.date())
        trans_time = st.time_input("거래시각", value=sample_dt.time(), step=60)
        cc_num = st.number_input(
            "카드번호",
            min_value=0,
            value=int(sample["cc_num"]),
            step=1,
            format="%d",
        )
        merchant = st.text_input("가맹점", sample["merchant"])
    with col2:
        amt = st.number_input(
            "금액",
            min_value=0.01,
            value=float(sample["amt"]),
            step=10.0,
            format="%.2f",
        )
        category = st.text_input("카테고리", sample["category"])
        city = st.text_input("도시", sample["city"])
        state = st.text_input("State", sample["state"])

    trans_datetime = datetime.combine(trans_date, trans_time).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "trans_num": trans_num.strip(),
        "trans_date_trans_time": trans_datetime,
        "cc_num": int(cc_num),
        "merchant": merchant.strip(),
        "amt": amt,
        "category": category.strip(),
        "city": city.strip(),
        "state": state.strip(),
    }


def render_metric(label: str, value: str, subtext: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _node_status(node_id: str, step: int, traces_by_id: dict, running_step: int) -> str:
    if node_id in traces_by_id:
        return "완료"
    if running_step == step:
        return "진행중"
    return "대기"


def _status_style(status: str) -> tuple[str, str]:
    if status == "완료":
        return "#dff4ec", "#1f6a43"
    if status == "진행중":
        return "#fff4db", "#8a5a00"
    return "#eef2f7", "#667487"


def _hover_text(label: str, status: str, trace: Optional[dict]) -> str:
    lines = [f"<b>{label}</b>", f"상태: {status}"]
    if trace:
        lines.extend(summarize_trace(trace))
    else:
        lines.append("생성 데이터 없음")
    return "<br>".join(lines)


def build_process_figure(node_traces: list[dict], running_step: int = 0) -> go.Figure:
    traces_by_id = {trace["id"]: trace for trace in node_traces}
    x_positions = list(range(len(NODE_DEFINITIONS)))
    y_positions = [0] * len(NODE_DEFINITIONS)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_positions,
            y=y_positions,
            mode="lines",
            line=dict(color="#c4cfdd", width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    for step, (node_id, label, _focus_key) in enumerate(NODE_DEFINITIONS, start=1):
        status = _node_status(node_id, step, traces_by_id, running_step)
        fill, border = _status_style(status)
        trace = traces_by_id.get(node_id)
        x = step - 1

        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[0],
                mode="markers+text",
                marker=dict(
                    size=42,
                    color=fill,
                    line=dict(color=border, width=2),
                    symbol="square",
                ),
                text=[str(step)],
                textposition="middle center",
                textfont=dict(color=border, size=13),
                hovertemplate=_hover_text(label, status, trace) + "<extra></extra>",
                showlegend=False,
            )
        )
        fig.add_annotation(
            x=x,
            y=-0.34,
            text=label,
            showarrow=False,
            font=dict(size=11, color="#17212f"),
            align="center",
        )
        fig.add_annotation(
            x=x,
            y=0.34,
            text=status,
            showarrow=False,
            font=dict(size=10, color=border),
            align="center",
        )

    fig.update_layout(
        height=210,
        margin=dict(l=10, r=10, t=20, b=45),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(visible=False, range=[-0.5, len(NODE_DEFINITIONS) - 0.5]),
        yaxis=dict(visible=False, range=[-0.7, 0.7]),
        hoverlabel=dict(bgcolor="white", bordercolor="#d9e0ea", font_size=12),
    )
    return fig


def render_process_graph(
    node_traces: list[dict],
    running_step: int = 0,
    key: str = "process-graph",
):
    st.markdown("### 프로세스 그래프")
    st.plotly_chart(
        build_process_figure(node_traces, running_step),
        use_container_width=True,
        config={"displayModeBar": False},
        key=key,
    )


def render_process_graph_only(
    node_traces: list[dict],
    running_step: int = 0,
    key: str = "process-graph-compact",
):
    st.plotly_chart(
        build_process_figure(node_traces, running_step),
        use_container_width=True,
        config={"displayModeBar": False},
        key=key,
    )


def format_json_value(value):
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "예" if value else "아니오"
    if isinstance(value, float):
        return f"{value:.4f}" if abs(value) < 10 else f"{value:.2f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def summarize_trace(trace: dict) -> list[str]:
    node_id = trace.get("id")
    data = trace.get("focus_data")

    if node_id == "transaction_analyzer":
        if not isinstance(data, dict):
            return ["생성 데이터 없음"]
        return [
            f"금액: ${format_json_value(data.get('amount'))}",
            f"시간대: {format_json_value(data.get('hour_of_day'))}시",
            f"야간 거래: {format_json_value(data.get('is_night_transaction'))}",
        ]
    if node_id == "customer_profile_tool":
        if not isinstance(data, dict):
            return ["생성 데이터 없음"]
        return [
            f"평균 결제금액: ${format_json_value(data.get('avg_amount_30d'))}",
            f"금액 Z-score: {format_json_value(data.get('amount_z_score'))}",
            f"미사용 카테고리: {format_json_value(data.get('is_unusual_category'))}",
        ]
    if node_id == "merchant_risk_assessor":
        if not isinstance(data, dict):
            return ["생성 데이터 없음"]
        return [
            f"가맹점 위험도: {format_json_value(data.get('risk_level'))}",
            f"차지백 비율: {format_json_value(data.get('chargeback_rate'))}",
            f"사기 신고 건수: {format_json_value(data.get('fraud_report_count'))}",
        ]
    if node_id == "velocity_checker":
        if not isinstance(data, dict):
            return ["생성 데이터 없음"]
        return [
            f"최근 1시간: {format_json_value(data.get('txn_last_1h'))}",
            f"최근 24시간: {format_json_value(data.get('txn_last_24h'))}",
            f"빈도 이상: {format_json_value(data.get('velocity_flag'))}",
        ]
    if node_id == "rule_based_scorer":
        return [
            f"발동 룰: {format_json_value(trace.get('updates', {}).get('rule_hits'))}",
            f"룰 점수: {format_json_value(trace.get('updates', {}).get('rule_score'))}",
        ]
    if node_id == "ml_fraud_scorer":
        return [f"ML 점수: {format_json_value(trace.get('updates', {}).get('ml_score'))}"]
    if node_id == "action_decision_maker":
        return [
            f"위험등급: {format_json_value(trace.get('updates', {}).get('risk_level'))}",
            f"조치: {format_json_value(trace.get('updates', {}).get('action_decision'))}",
        ]
    if node_id == "report_generator":
        report = trace.get("updates", {}).get("report") or ""
        first_line = report.strip().splitlines()[0] if report.strip() else "리포트 생성 완료"
        return [first_line[:80]]

    if not isinstance(data, dict):
        return [format_json_value(data)] if data is not None else ["생성 데이터 없음"]

    return [f"{key}: {format_json_value(value)}" for key, value in list(data.items())[:3]]


def render_process_flow(
    node_traces: list[dict],
    running_step: int = 0,
    key_prefix: str = "process-flow",
):
    traces_by_id = {trace["id"]: trace for trace in node_traces}
    render_process_graph(node_traces, running_step, key=f"{key_prefix}-graph")
    st.markdown("### 단계 요약")

    rows = []
    for step, (node_id, label, _focus_key) in enumerate(NODE_DEFINITIONS, start=1):
        trace = traces_by_id.get(node_id)
        if trace:
            status = "완료"
            summary = " / ".join(summarize_trace(trace))
        elif running_step == step:
            status = "진행중"
            summary = "현재 실행 중"
        else:
            status = "대기"
            summary = "-"

        rows.append(
            {
                "step": step,
                "status": status,
                "node": label,
                "summary": summary,
            }
        )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "step": st.column_config.NumberColumn("Step", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "node": st.column_config.TextColumn("Node", width="medium"),
            "summary": st.column_config.TextColumn("Summary", width="large"),
        },
    )

    selected_step = st.selectbox(
        "단계 상세",
        options=[row["step"] for row in rows],
        format_func=lambda step: f"{step}. {rows[step - 1]['node']}",
    )
    selected_node_id = NODE_DEFINITIONS[selected_step - 1][0]
    selected_trace = traces_by_id.get(selected_node_id)
    if selected_trace:
        st.markdown("#### 선택 단계 결과")
        for line in summarize_trace(selected_trace):
            st.write(f"- {line}")
    else:
        st.info("아직 실행되지 않은 단계입니다.")


def get_request_progress(request: dict) -> tuple[int, int, str]:
    node_traces = request.get("node_traces") or []
    total_steps = len(NODE_DEFINITIONS)
    completed_steps = len(node_traces)
    current_node = node_traces[-1]["label"] if node_traces else "대기"
    if completed_steps < total_steps and completed_steps > 0:
        current_node = f"{current_node} 이후"
    return completed_steps, total_steps, current_node


def render_node_grid(node_traces: list[dict]):
    if not node_traces:
        st.info("노드 실행 이력이 없습니다.")
        return

    selected_index = st.selectbox(
        "노드 선택",
        options=list(range(len(node_traces))),
        format_func=lambda idx: f"{node_traces[idx]['step']}. {node_traces[idx]['label']}",
    )
    node = node_traces[selected_index]

    meta_col, summary_col = st.columns([0.32, 0.68])
    with meta_col:
        st.markdown(
            f"""
            <div class="node-card">
                <div class="node-step">STEP {node["step"]} / {node["total_steps"]}</div>
                <div class="node-title">{node["label"]}</div>
                <div class="node-status">완료</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with summary_col:
        st.subheader("핵심 결과")
        for line in summarize_trace(node):
            st.write(f"- {line}")

    data_tab, update_tab = st.tabs(["생성 데이터", "State 업데이트"])
    with data_tab:
        st.json(node.get("focus_data"))
    with update_tab:
        st.json(node.get("updates") or {})


def render_hero(page: str):
    subtitle_map = {
        "요청 생성": "새 조사 요청을 만들고, 8단계 분석 파이프라인이 어떻게 진행되는지 바로 확인합니다.",
        "요청 리스트": "동시에 들어온 요청들의 상태를 한 번에 보고, 어느 단계에 머물러 있는지 빠르게 확인합니다.",
        "요청 상세": "선택한 요청 하나를 기준으로 각 노드의 결과와 최종 리포트를 추적합니다.",
    }
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">Fraud Investigation Dashboard</div>
            <div class="hero-title">{page}</div>
            <div class="hero-subtitle">{subtitle_map[page]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
