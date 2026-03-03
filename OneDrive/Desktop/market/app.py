"""
Market Trend Analyzer — Streamlit UI
Premium-styled agentic dashboard with state machine visualization,
tool call logs, trend graphs, and metrics.
"""

import streamlit as st
import pandas as pd
import json
import time

from agent.trend_agent import TrendAgent
from agent.state_machine import AgentState
from database.logger import DBLogger

# ─── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Trend Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Import Google Font ─────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ─────────────────────────────────────────────────── */
    * { font-family: 'Inter', sans-serif; }
    .stApp {
        background: linear-gradient(135deg, #0a0e17 0%, #0d1321 40%, #111827 100%);
    }

    /* ── Sidebar ────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1724 0%, #131b2e 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.15);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* ── Header ─────────────────────────────────────────────────── */
    .main-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(139,92,246,0.08) 100%);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 28px;
        backdrop-filter: blur(12px);
    }
    .main-header h1 {
        background: linear-gradient(135deg, #818cf8, #a78bfa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1rem;
        margin: 0;
        font-weight: 400;
    }

    /* ── State Badge ────────────────────────────────────────────── */
    .state-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 22px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        animation: pulse-glow 2s ease-in-out infinite;
    }
    .state-idle        { background: rgba(100,116,139,0.2); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }
    .state-load_csv    { background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
    .state-analyze     { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .state-insight     { background: rgba(139,92,246,0.2); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
    .state-completed   { background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
    .state-error       { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }

    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 8px rgba(99,102,241,0.15); }
        50%      { box-shadow: 0 0 20px rgba(99,102,241,0.3); }
    }

    /* ── Metric Card ────────────────────────────────────────────── */
    .metric-card {
        background: linear-gradient(145deg, rgba(30,37,56,0.8), rgba(22,28,45,0.9));
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 14px;
        padding: 22px 26px;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
    }
    .metric-card:hover {
        border-color: rgba(99,102,241,0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(99,102,241,0.12);
    }
    .metric-label {
        color: #64748b;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-unit {
        color: #475569;
        font-size: 0.75rem;
        margin-top: 4px;
    }

    /* ── Timeline ───────────────────────────────────────────────── */
    .timeline-item {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 12px 18px;
        margin: 6px 0;
        background: rgba(30,37,56,0.5);
        border-radius: 10px;
        border-left: 3px solid #6366f1;
        transition: all 0.2s ease;
    }
    .timeline-item:hover {
        background: rgba(30,37,56,0.8);
    }
    .timeline-arrow {
        color: #6366f1;
        font-weight: 700;
        font-size: 1rem;
    }
    .timeline-state {
        color: #e2e8f0;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .timeline-event {
        color: #818cf8;
        font-size: 0.75rem;
        font-style: italic;
        font-weight: 500;
    }
    .timeline-time {
        color: #475569;
        font-size: 0.7rem;
        margin-left: auto;
    }

    /* ── Section Header ─────────────────────────────────────────── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 30px 0 16px 0;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(99,102,241,0.12);
    }
    .section-header h3 {
        color: #e2e8f0;
        font-size: 1.1rem;
        font-weight: 700;
        margin: 0;
    }

    /* ── Info Card ───────────────────────────────────────────────── */
    .info-card {
        background: linear-gradient(145deg, rgba(30,37,56,0.6), rgba(22,28,45,0.7));
        border: 1px solid rgba(99,102,241,0.12);
        border-radius: 12px;
        padding: 20px 24px;
        margin: 8px 0;
    }
    .info-card p {
        color: #cbd5e1;
        margin: 4px 0;
        font-size: 0.9rem;
    }
    .info-card strong {
        color: #a5b4fc;
    }

    /* ── Log Entry ──────────────────────────────────────────────── */
    .log-entry {
        background: rgba(15,23,42,0.8);
        border: 1px solid rgba(99,102,241,0.1);
        border-radius: 10px;
        padding: 16px 20px;
        margin: 8px 0;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8rem;
        color: #94a3b8;
        overflow-x: auto;
    }
    .log-tool-name {
        color: #818cf8;
        font-weight: 700;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }
    .log-success { color: #34d399; }
    .log-fail    { color: #f87171; }

    /* ── Buttons ─────────────────────────────────────────────────── */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        border: none;
    }
    div[data-testid="stVerticalBlock"] > div:has(> .stButton) button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
    }

    /* ── Expander ────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: rgba(30,37,56,0.5);
        border-radius: 10px;
        color: #e2e8f0;
    }

    /* ── Hide Streamlit Branding ─────────────────────────────────── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ─────────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = None
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None


# ═══════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_state_class(state: AgentState) -> str:
    """Map an AgentState to a CSS class."""
    mapping = {
        AgentState.IDLE: "state-idle",
        AgentState.LOAD_CSV: "state-load_csv",
        AgentState.ANALYZE_TREND: "state-analyze",
        AgentState.GENERATE_INSIGHT: "state-insight",
        AgentState.COMPLETED: "state-completed",
        AgentState.ERROR: "state-error",
    }
    return mapping.get(state, "state-idle")


def get_state_icon(state: AgentState) -> str:
    icons = {
        AgentState.IDLE: "⏸️",
        AgentState.LOAD_CSV: "📂",
        AgentState.ANALYZE_TREND: "📊",
        AgentState.GENERATE_INSIGHT: "💡",
        AgentState.COMPLETED: "✅",
        AgentState.ERROR: "❌",
    }
    return icons.get(state, "⏸️")


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧠 Control Panel")
    st.markdown("---")

    # File upload
    st.markdown("### 📁 Data Source")
    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        help="Upload a CSV file with at least one numeric column for trend analysis.",
    )

    st.markdown("---")

    # Auto Seed Info
    st.markdown("### 🎲 Auto Seed")
    _db = DBLogger()
    _next_seed = _db.get_next_seed()
    st.markdown(f"""
    <div class="info-card">
        <p><strong>Next seed:</strong> {_next_seed}</p>
        <p style="color:#64748b; font-size:0.78rem;">Seeds auto-increment per run and persist across restarts.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Buttons
    col_start, col_reset = st.columns(2)
    with col_start:
        start_btn = st.button("🚀 Start", type="primary", use_container_width=True)
    with col_reset:
        reset_btn = st.button("🔄 Reset", use_container_width=True)

    st.markdown("---")

    # Agent Info
    if st.session_state.agent:
        agent = st.session_state.agent
        st.markdown("### 🤖 Agent Info")
        st.markdown(f"""
        <div class="info-card">
            <p><strong>Run ID:</strong> {agent.run_id[:8]}…</p>
            <p><strong>Seed:</strong> {agent.seed}</p>
            <p><strong>Steps:</strong> {agent.step_count} / 10</p>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>📈 Market Trend Analyzer</h1>
    <p>Agentic AI system for statistical trend detection &amp; structured insight generation</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  BUTTON HANDLERS
# ═══════════════════════════════════════════════════════════════════════

if reset_btn:
    st.session_state.agent = None
    st.session_state.analysis_complete = False
    st.session_state.uploaded_data = None
    st.rerun()

if start_btn:
    if uploaded_file is None:
        st.error("⚠️ Please upload a CSV file first.")
    else:
        # Create fresh agent (seed auto-retrieved from DB)
        agent = TrendAgent()
        st.session_state.agent = agent
        st.session_state.analysis_complete = False

        # Read file bytes
        file_bytes = uploaded_file.getvalue()
        st.session_state.uploaded_data = file_bytes

        # Run the analysis
        with st.spinner("🔄 Running agentic analysis pipeline…"):
            success = agent.run(file_bytes, uploaded_file.name)

        st.session_state.analysis_complete = True
        if success:
            st.toast("✅ Analysis completed!", icon="🎉")
        else:
            st.toast("❌ Analysis failed. Check error logs.", icon="⚠️")
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════

agent: TrendAgent = st.session_state.agent

if agent is None:
    # ── Welcome State ─────────────────────────────────────────────
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 4rem; margin-bottom: 16px;">🤖</div>
        <h2 style="color: #e2e8f0; font-weight: 700; margin-bottom: 8px;">Ready to Analyze</h2>
        <p style="color: #64748b; font-size: 1.05rem; max-width: 500px; margin: 0 auto;">
            Upload a CSV file with numeric time-series data and click <strong style="color:#818cf8;">Start</strong> to begin the agentic analysis pipeline. Seeds are managed automatically.
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    # ── Current State ─────────────────────────────────────────────
    state = agent.current_state
    state_cls = get_state_class(state)
    state_icon = get_state_icon(state)

    st.markdown(f"""
    <div class="section-header"><h3>🔵 Current Agent State</h3></div>
    <div style="margin-bottom: 24px;">
        <span class="state-badge {state_cls}">
            {state_icon} {state.value}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  METRICS ROW
    # ══════════════════════════════════════════════════════════════

    if st.session_state.analysis_complete:
        st.markdown('<div class="section-header"><h3>📊 Metrics Dashboard</h3></div>', unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)

        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⏱ Processing Time</div>
                <div class="metric-value">{agent.processing_time:.3f}</div>
                <div class="metric-unit">seconds</div>
            </div>
            """, unsafe_allow_html=True)

        with m2:
            slope = agent.trend_output.slope if agent.trend_output and agent.trend_output.success else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📐 Slope Magnitude</div>
                <div class="metric-value">{abs(slope):.6f}</div>
                <div class="metric-unit">units per period</div>
            </div>
            """, unsafe_allow_html=True)

        with m3:
            conf = agent.trend_output.confidence_score if agent.trend_output and agent.trend_output.success else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🎯 Confidence Score</div>
                <div class="metric-value">{conf:.2%}</div>
                <div class="metric-unit">trend reliability</div>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  TREND INSIGHT CARD
    # ══════════════════════════════════════════════════════════════

    if agent.trend_output and agent.trend_output.success:
        trend = agent.trend_output
        trend_emoji = {"UPTREND": "🟢 📈", "DOWNTREND": "🔴 📉", "SIDEWAYS": "🟡 ➡️"}
        emoji = trend_emoji.get(trend.trend_classification.value, "⚪")

        st.markdown(f"""
        <div class="section-header"><h3>💡 Trend Insight</h3></div>
        <div class="info-card">
            <p style="font-size:1.3rem; font-weight:700; color:#e2e8f0; margin-bottom:12px;">
                {emoji} {trend.trend_classification.value}
            </p>
            <p><strong>Slope:</strong> {trend.slope:.6f}</p>
            <p><strong>Intercept:</strong> {trend.intercept:.4f}</p>
            <p><strong>Std Deviation:</strong> {trend.standard_deviation:.4f}</p>
            <p><strong>Mean Value:</strong> {trend.mean_value:.4f}</p>
            <p><strong>Data Points:</strong> {trend.data_points}</p>
            <p><strong>Moving Avg Window:</strong> {trend.moving_average_window}</p>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  TREND GRAPH
    # ══════════════════════════════════════════════════════════════

    if agent.figure is not None:
        st.markdown('<div class="section-header"><h3>📉 Trend Visualization</h3></div>', unsafe_allow_html=True)
        st.pyplot(agent.figure, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    #  STATE TRANSITION HISTORY
    # ══════════════════════════════════════════════════════════════

    st.markdown('<div class="section-header"><h3>🔄 State Transition History</h3></div>', unsafe_allow_html=True)

    history = agent.transition_history
    if history:
        for record in history:
            st.markdown(f"""
            <div class="timeline-item">
                <span class="timeline-state">{record['previous_state']}</span>
                <span class="timeline-arrow">→</span>
                <span class="timeline-event">{record['event']}</span>
                <span class="timeline-arrow">→</span>
                <span class="timeline-state">{record['next_state']}</span>
                <span class="timeline-time">{record['timestamp']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#475569; font-style:italic;">No transitions yet.</p>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  TOOL CALL LOGS
    # ══════════════════════════════════════════════════════════════

    st.markdown('<div class="section-header"><h3>🔧 Tool Call Logs</h3></div>', unsafe_allow_html=True)

    if agent.tool_logs:
        for i, log in enumerate(agent.tool_logs_dicts):
            success_cls = "log-success" if log["success"] else "log-fail"
            success_label = "✅ Success" if log["success"] else "❌ Failed"

            with st.expander(f"🔧 {log['tool_name']}  •  {log['duration_seconds']:.4f}s  •  {success_label}", expanded=False):
                st.markdown(f"""
                <div class="log-entry">
                    <div class="log-tool-name">{log['tool_name']}</div>
                    <div class="{success_cls}" style="margin-bottom:10px; font-weight:600;">{success_label} — {log['duration_seconds']:.4f}s</div>
                    <div style="margin-bottom:8px;">
                        <strong style="color:#818cf8;">Input:</strong>
                        <pre style="color:#94a3b8; margin:4px 0; white-space:pre-wrap;">{json.dumps(log['input_data'], indent=2)}</pre>
                    </div>
                    <div>
                        <strong style="color:#818cf8;">Output:</strong>
                        <pre style="color:#94a3b8; margin:4px 0; white-space:pre-wrap;">{json.dumps(log['output_data'], indent=2, default=str)}</pre>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#475569; font-style:italic;">No tool calls recorded yet.</p>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  ERROR DISPLAY
    # ══════════════════════════════════════════════════════════════

    if agent.error_message:
        st.markdown(f"""
        <div class="section-header"><h3>⚠️ Error Details</h3></div>
        <div class="info-card" style="border-color: rgba(239,68,68,0.3);">
            <p style="color:#f87171; font-weight:600;">{agent.error_message}</p>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  DATA PREVIEW
    # ══════════════════════════════════════════════════════════════

    if agent.dataframe is not None:
        st.markdown('<div class="section-header"><h3>📋 Data Preview</h3></div>', unsafe_allow_html=True)
        st.dataframe(agent.dataframe.head(20), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════
#  SEED HISTORY (always visible)
# ═══════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header"><h3>🎲 Seed History</h3></div>', unsafe_allow_html=True)

_history_db = DBLogger()
seed_history = _history_db.get_seed_history(limit=20)

if seed_history:
    history_df = pd.DataFrame(seed_history)
    history_df.columns = ["Run ID", "Seed", "Timestamp"]
    st.dataframe(history_df, use_container_width=True, hide_index=True)
else:
    st.markdown('<p style="color:#475569; font-style:italic;">No runs recorded yet. Start an analysis to see seed history.</p>', unsafe_allow_html=True)
