import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from frontend.pages import (
    init_state,
    render_request_create,
    render_request_detail,
    render_request_list,
)
from frontend.styles import render_styles

st.set_page_config(page_title="Fraud Investigator", page_icon="FI", layout="wide")


PAGE_TO_QUERY = {
    "요청 생성": "create",
    "요청 리스트": "list",
    "요청 상세": "detail",
}
QUERY_TO_PAGE = {value: key for key, value in PAGE_TO_QUERY.items()}
NAV_ITEMS = [
    ("요청 생성", "요청 생성", "새 조사 요청 생성", "create"),
    ("요청 리스트", "요청 리스트", "요청 목록 및 상태 확인", "list"),
]


def sync_page_from_query():
    page_key = st.query_params.get("page")
    if isinstance(page_key, list):
        page_key = page_key[0] if page_key else None
    if page_key in QUERY_TO_PAGE:
        st.session_state.page = QUERY_TO_PAGE[page_key]

    rid = st.query_params.get("rid")
    if isinstance(rid, list):
        rid = rid[0] if rid else None
    if rid:
        st.session_state.selected_request_id = rid


def render_sidebar():
    requests = st.session_state.requests
    request_count = len(requests)
    high_count = sum(
        1
        for request in requests
        if (request.get("result") or {}).get("risk_level") in ("high", "critical")
    )
    st.sidebar.markdown(
        """
        <div class="sidebar-section-label">Menu</div>
        """,
        unsafe_allow_html=True,
    )

    nav_markup = ['<nav class="sidebar-nav">']
    for page_name, title, description, query in NAV_ITEMS:
        active = " active" if st.session_state.page == page_name else ""
        nav_markup.append(
            f'<a class="sidebar-nav-item{active}" href="?page={query}" target="_self">'
            f'<span class="nav-title">{title}</span>'
            f'<span class="nav-desc">{description}</span>'
            "</a>"
        )
    nav_markup.append("</nav>")
    st.sidebar.markdown("\n".join(nav_markup), unsafe_allow_html=True)

    st.sidebar.markdown(
        f"""
        <div class="sidebar-section-label">Queue</div>
        <div class="sidebar-summary">
            <div class="sidebar-summary-row">
                <span>Total Requests</span>
                <span class="sidebar-summary-value">{request_count}</span>
            </div>
            <div class="sidebar-summary-row">
                <span>High Risk</span>
                <span class="sidebar-summary-value danger">{high_count}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    init_state()
    sync_page_from_query()
    render_styles()

    render_sidebar()
    page = st.session_state.page

    if page == "요청 생성":
        render_request_create()
    elif page == "요청 리스트":
        render_request_list()
    else:
        render_request_detail()


if __name__ == "__main__":
    main()
