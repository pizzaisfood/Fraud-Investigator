import streamlit as st


_DASHBOARD_CSS = """
<style>
:root {
    --bg: #f5f7fb;
    --surface: #ffffff;
    --surface-muted: #f8fafc;
    --border: #d9e0ea;
    --border-strong: #c4cfdd;
    --text: #17212f;
    --text-muted: #667487;
    --sidebar-bg: #111827;
    --sidebar-border: #1f2937;
    --primary: #2563eb;
    --success-bg: #e8f5ee;
    --success-text: #1f6a43;
    --warn-bg: #fff4db;
    --warn-text: #8a5a00;
    --danger-bg: #fde8e8;
    --danger-text: #a72b2b;
}
.stApp {
    background: var(--bg);
    color: var(--text);
}
h1, h2, h3 {
    letter-spacing: -0.02em;
    color: var(--text);
}
[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(17, 24, 39, 0.98)),
        radial-gradient(circle at 20% 0%, rgba(37, 99, 235, 0.22), transparent 28%);
    border-right: 1px solid var(--sidebar-border);
}
[data-testid="stSidebar"] * {
    color: #e5e7eb;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.25rem 0.85rem 1rem 0.85rem;
}
.sidebar-section-label {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0.2rem 0 0.5rem 0.15rem;
}
.sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.sidebar-nav-item {
    display: block;
    text-decoration: none !important;
    border-radius: 14px;
    padding: 12px 13px;
    border: 1px solid transparent;
    background: transparent;
    transition: background 0.14s ease, border-color 0.14s ease, transform 0.14s ease;
}
.sidebar-nav-item:hover {
    background: rgba(148, 163, 184, 0.12);
    border-color: rgba(148, 163, 184, 0.18);
    transform: translateX(2px);
}
.sidebar-nav-item.active {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(15, 118, 110, 0.16));
    border-color: rgba(96, 165, 250, 0.42);
    box-shadow: inset 3px 0 0 #60a5fa;
}
.nav-title {
    display: block;
    color: #ffffff;
    font-size: 14px;
    line-height: 1.2;
    font-weight: 800;
}
.nav-desc {
    display: block;
    color: #94a3b8;
    font-size: 11px;
    line-height: 1.35;
    margin-top: 5px;
}
.sidebar-nav-item.active .nav-desc {
    color: #bfdbfe;
}
.sidebar-summary {
    background: rgba(15, 23, 42, 0.64);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 14px;
    padding: 12px;
    margin-top: 0;
}
.sidebar-summary-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    color: #cbd5e1;
    font-size: 12px;
    margin-bottom: 6px;
}
.sidebar-summary-row:last-child {
    margin-bottom: 0;
}
.sidebar-summary-value {
    color: #ffffff;
    font-weight: 700;
}
.sidebar-summary-value.danger {
    color: #fca5a5;
}
.sidebar-selected-card {
    background: rgba(37, 99, 235, 0.12);
    border: 1px solid rgba(96, 165, 250, 0.30);
    border-radius: 14px;
    padding: 12px;
}
.selected-label {
    color: #93c5fd;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 700;
    margin-bottom: 6px;
}
.selected-value {
    color: #ffffff;
    font-size: 13px;
    font-weight: 750;
    word-break: break-all;
}
[data-testid="stSidebar"] [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 7px;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    min-height: 42px;
    padding: 0 12px;
    border-radius: 12px;
    border: 1px solid transparent;
    background: transparent;
    transition: background 0.12s ease, border-color 0.12s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(148, 163, 184, 0.12);
    border-color: rgba(148, 163, 184, 0.18);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(37, 99, 235, 0.18);
    border-color: rgba(96, 165, 250, 0.40);
    box-shadow: inset 3px 0 0 #60a5fa;
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
    color: #dbeafe;
    font-weight: 700;
    font-size: 14px;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
    color: #ffffff;
}
[data-testid="stSidebar"] [role="radio"] > div:first-child {
    display: none;
}
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {
    display: none;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
    display: none;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:last-child {
    width: 100%;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: rgba(255, 255, 255, 0.06);
    color: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 12px !important;
    padding: 0.58rem 0.75rem;
    font-weight: 700;
    box-shadow: none;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(37, 99, 235, 0.22);
    border-color: rgba(96, 165, 250, 0.42);
}
.hero-card {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: none;
    margin-bottom: 14px;
}
.hero-kicker {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 4px;
    font-weight: 600;
}
.hero-title {
    font-size: 20px;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 4px;
}
.hero-subtitle {
    font-size: 13px;
    line-height: 1.45;
    color: var(--text-muted);
}
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    min-height: 92px;
    box-shadow: none;
}
.metric-label {
    color: var(--text-muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    font-weight: 600;
}
.metric-value {
    color: var(--text);
    font-size: 22px;
    font-weight: 700;
}
.metric-sub {
    color: var(--text-muted);
    font-size: 13px;
    margin-top: 8px;
}
.node-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 4px solid var(--border-strong);
    border-radius: 10px;
    padding: 16px 16px 10px 16px;
    min-height: 120px;
    margin-bottom: 12px;
    box-shadow: none;
}
.node-step {
    color: var(--text-muted);
    font-size: 12px;
    margin-bottom: 8px;
}
.node-title {
    color: var(--text);
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 8px;
}
.node-status {
    display: inline-block;
    background: var(--success-bg);
    color: var(--success-text);
    border-radius: 999px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 12px;
}
.list-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 14px;
    box-shadow: none;
}
.list-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}
.list-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 4px;
}
.list-sub {
    color: var(--text-muted);
    font-size: 13px;
}
.status-pill {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.status-completed {
    background: var(--success-bg);
    color: var(--success-text);
}
.status-running {
    background: var(--warn-bg);
    color: var(--warn-text);
}
.status-failed {
    background: var(--danger-bg);
    color: var(--danger-text);
}
.mini-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin: 12px 0;
}
.mini-stat {
    background: var(--surface-muted);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
}
.mini-label {
    color: var(--text-muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 6px;
    font-weight: 600;
}
.mini-value {
    color: var(--text);
    font-size: 18px;
    font-weight: 700;
}
.section-label {
    color: var(--text-muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    font-weight: 700;
}
.progress-note {
    color: var(--text-muted);
    font-size: 13px;
    margin-top: 6px;
}
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 16px;
    margin: 2px 0 18px 0;
}
.page-title {
    color: var(--text);
    font-size: 28px;
    line-height: 1.15;
    font-weight: 800;
    letter-spacing: -0.03em;
}
.page-subtitle {
    color: var(--text-muted);
    font-size: 14px;
    margin-top: 8px;
}
.list-count-card {
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    color: var(--text-muted);
    font-size: 13px;
}
.list-count-card strong {
    color: var(--text);
    font-size: 18px;
    margin: 0 4px;
}
.empty-state {
    background: var(--surface);
    border: 1px dashed var(--border-strong);
    border-radius: 12px;
    padding: 34px 28px;
    margin-top: 16px;
    text-align: center;
}
.empty-title {
    color: var(--text);
    font-size: 18px;
    font-weight: 750;
    margin-bottom: 8px;
}
.empty-desc {
    color: var(--text-muted);
    font-size: 14px;
}
.request-table-wrap {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-top: 8px;
}
.request-table-head {
    display: grid;
    grid-template-columns: 1.22fr 1.1fr 0.65fr 0.78fr 1fr 0.75fr;
    gap: 14px;
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 12px 16px;
    background: var(--surface-muted);
    border-bottom: 1px solid var(--border);
}
.table-row {
    display: grid;
    grid-template-columns: 1.22fr 1.1fr 0.65fr 0.78fr 1fr 0.75fr;
    gap: 14px;
    padding: 10px 16px;
    align-items: center;
    border-bottom: 1px solid var(--border);
    text-decoration: none !important;
    transition: background 0.1s;
}
.table-row:last-child {
    border-bottom: none;
}
.table-row:hover {
    background: var(--surface-muted);
}
.table-row:hover .table-detail-btn {
    border-color: var(--primary);
    color: var(--primary);
}
.table-main {
    color: var(--text);
    font-size: 13px;
    font-weight: 750;
    line-height: 1.25;
}
.table-sub {
    color: var(--text-muted);
    font-size: 12px;
    line-height: 1.35;
    margin-top: 3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.table-action-cell {
    display: flex;
    align-items: center;
}
.table-detail-btn {
    display: inline-block;
    padding: 5px 10px;
    border: 1px solid var(--border-strong);
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    background: transparent;
    white-space: nowrap;
}
.stProgress > div > div > div > div {
    background: var(--primary);
}
.request-list-item {
    padding: 14px 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    margin-bottom: 10px;
}
[data-testid="stForm"], .stButton > button, .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
    border-radius: 8px !important;
}
.stButton > button {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border-strong);
    font-weight: 600;
    font-size: 13px;
    box-shadow: none;
}
.stButton > button:hover {
    background: var(--surface-muted);
    border-color: var(--primary);
    color: var(--primary);
}
[data-testid="baseButton-primary"] {
    background: var(--primary) !important;
    color: #ffffff !important;
    border-color: var(--primary) !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
    color: #ffffff !important;
}
.table-action-spacer {
    height: 10px;
}
div[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
}
.dashboard-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}
.toolbar-meta {
    color: var(--text-muted);
    font-size: 12px;
    font-weight: 500;
    text-align: right;
}
</style>
"""


def render_styles():
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)
