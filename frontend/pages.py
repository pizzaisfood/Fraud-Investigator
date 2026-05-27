import streamlit as st

from services.investigate import investigate_with_trace
from services.request_store import load_requests, save_request

from frontend.components import (
    build_transaction_form,
    get_request_progress,
    render_hero,
    render_metric,
    render_node_grid,
    render_process_flow,
    render_process_graph_only,
    summarize_trace,
)

PAGE_TO_QUERY = {
    "요청 생성": "create",
    "요청 리스트": "list",
    "요청 상세": "detail",
}


def _request_table_rows(requests: list[dict]) -> list[dict]:
    rows = []
    for request in requests:
        result = request.get("result") or {}
        completed_steps, total_steps, current_node = get_request_progress(request)
        ml_score = result.get("ml_score")
        rows.append(
            {
                "request_id": request["request_id"],
                "created_at": request["created_at"],
                "transaction_id": request["transaction"].get("trans_num", "-"),
                "merchant": request["transaction"].get("merchant", "-"),
                "risk_level": result.get("risk_level") or "-",
                "action": result.get("action_decision") or "-",
                "rule_score": result.get("rule_score") or 0,
                "ml_score": round(ml_score, 4) if ml_score is not None else None,
                "progress": f"{completed_steps}/{total_steps}",
                "current_node": current_node,
            }
        )
    return rows


def init_state():
    if "requests" not in st.session_state:
        st.session_state.requests = load_requests()
    st.session_state.setdefault("selected_request_id", None)
    st.session_state.setdefault("page", "요청 생성")
    st.session_state.setdefault("request_table_selection", None)


def render_request_create():
    st.subheader("새 조사 요청")
    transaction = build_transaction_form()
    with st.expander("입력 데이터 미리보기", expanded=False):
        st.json(transaction)

    if st.button("요청 생성 및 분석", type="primary", use_container_width=True):
        compact_flow = st.empty()
        progress = st.progress(0)
        status = st.empty()
        current_step = st.empty()
        live_traces: list[dict] = []

        def on_step_start(trace: dict, index: int, total: int, _state: dict):
            progress.progress(index / total)
            status.info(f"{index}/{total} 단계 진행 중: {trace['label']}")
            with current_step.container():
                st.markdown("#### 현재 단계")
                render_metric("실행 노드", trace["label"], f"{index}/{total}")
                st.write("- 실행 중")
            with compact_flow.container():
                render_process_graph_only(
                    live_traces,
                    index,
                    key=f"create-process-start-{index}",
                )

        def on_step_end(trace: dict, index: int, total: int, _state: dict):
            live_traces.append(trace)
            progress.progress(index / total)
            status.success(f"{index}/{total} 단계 완료: {trace['label']}")
            with current_step.container():
                st.markdown("#### 최근 완료 단계")
                render_metric("완료 노드", trace["label"], f"{index}/{total}")
                for line in summarize_trace(trace):
                    st.write(f"- {line}")
            with compact_flow.container():
                render_process_graph_only(
                    live_traces,
                    index + 1 if index < total else 0,
                    key=f"create-process-end-{index}",
                )

        try:
            request_record = investigate_with_trace(
                transaction,
                on_step_start=on_step_start,
                on_step_end=on_step_end,
            )
        except Exception as exc:
            st.error(str(exc))
        else:
            save_request(request_record)
            st.session_state.requests.insert(0, request_record)
            st.session_state.selected_request_id = request_record["request_id"]
            st.session_state.page = "요청 상세"
            st.query_params["page"] = PAGE_TO_QUERY["요청 상세"]
            status.success("분석이 완료되었습니다.")
            st.rerun()


def render_request_list():
    requests = st.session_state.requests

    st.markdown(
        """
        <div class="page-header">
            <div>
                <div class="page-title">요청 리스트</div>
                <div class="page-subtitle">생성된 조사 요청을 확인하고 상세 버튼으로 결과 화면으로 이동합니다.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_col, count_col = st.columns([0.24, 0.76])
    with action_col:
        if st.button("새 요청 생성", type="primary", use_container_width=True):
            st.session_state.page = "요청 생성"
            st.query_params["page"] = PAGE_TO_QUERY["요청 생성"]
            st.rerun()
    with count_col:
        st.markdown(
            f'<div class="list-count-card">현재 요청 <strong>{len(requests)}</strong>건</div>',
            unsafe_allow_html=True,
        )

    if not requests:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-title">생성된 요청이 없습니다.</div>
                <div class="empty-desc">새 요청을 생성하면 이 화면에서 진행 상태와 최종 결과를 확인할 수 있습니다.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    rows = _request_table_rows(requests)
    html = ['<div class="request-table-wrap">']
    html.append(
        '<div class="request-table-head">'
        "<span>Request</span><span>Transaction</span><span>Risk</span>"
        "<span>Score</span><span>Progress</span><span></span>"
        "</div>"
    )
    for row in rows:
        ml_score = "-" if row["ml_score"] is None else f"{row['ml_score']:.4f}"
        html.append(
            f'<a class="table-row" href="?page=detail&rid={row["request_id"]}" target="_self">'
            f'<div><div class="table-main">{row["request_id"]}</div><div class="table-sub">{row["created_at"]}</div></div>'
            f'<div><div class="table-main">{row["transaction_id"]}</div><div class="table-sub">{row["merchant"]}</div></div>'
            f'<div><div class="table-main">{row["risk_level"]}</div><div class="table-sub">{row["action"]}</div></div>'
            f'<div><div class="table-main">Rule {row["rule_score"]}</div><div class="table-sub">ML {ml_score}</div></div>'
            f'<div><div class="table-main">{row["progress"]}</div><div class="table-sub">{row["current_node"]}</div></div>'
            f'<div class="table-action-cell"><span class="table-detail-btn">상세 보기</span></div>'
            f"</a>"
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_request_detail():
    selected_request_id = st.session_state.selected_request_id
    requests = st.session_state.requests
    request = next((item for item in requests if item["request_id"] == selected_request_id), None)

    if request is None:
        st.info("선택된 요청이 없습니다.")
        return

    result = request.get("result") or {}
    completed_steps, total_steps, current_node = get_request_progress(request)
    progress_ratio = completed_steps / total_steps

    top1, top2, top3 = st.columns(3)
    with top1:
        render_metric("위험등급", str(result.get("risk_level") or "-"), request["request_id"])
    with top2:
        render_metric("조치", str(result.get("action_decision") or "-"), request["created_at"])
    with top3:
        ml_score = result.get("ml_score")
        ml_text = f"{ml_score * 100:.1f}%" if ml_score is not None else "N/A"
        render_metric("ML 점수", ml_text, f"룰 점수 {result.get('rule_score') or 0}")

    st.progress(progress_ratio)
    st.markdown(
        f'<div class="progress-note">노드 진행률 {completed_steps}/{total_steps} · 현재 기준 노드: {current_node}</div>',
        unsafe_allow_html=True,
    )

    overview_tab, process_tab, data_tab, report_tab = st.tabs(
        ["요약", "프로세스", "노드 데이터", "리포트"]
    )

    with overview_tab:
        left, right = st.columns([0.42, 0.58])
        with left:
            st.subheader("거래 정보")
            st.json(request.get("transaction") or {})
        with right:
            st.subheader("최종 결과")
            st.json(result)

    with process_tab:
        render_process_flow(
            request.get("node_traces") or [],
            key_prefix=f"detail-{request['request_id']}",
        )

    with data_tab:
        render_node_grid(request.get("node_traces") or [])

    with report_tab:
        st.markdown(result.get("report") or "(리포트 없음)")
