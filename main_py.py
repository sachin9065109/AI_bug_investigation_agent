import streamlit as st
import google.generativeai as genai
import json
import re
from datetime import datetime

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Bug Investigation Agent",
    page_icon="🔍",
    layout="wide",
)

# ─── CSS Styling ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 8px; }
    .feature-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .badge-core    { background: #dbeafe; color: #1e40af; }
    .badge-adv     { background: #fef3c7; color: #92400e; }
    .badge-pro     { background: #fee2e2; color: #991b1b; }
    .result-box {
        background: #f8fafc;
        border-left: 4px solid #6366f1;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }
    .severity-critical { color: #dc2626; font-weight: 700; }
    .severity-high     { color: #ea580c; font-weight: 700; }
    .severity-medium   { color: #ca8a04; font-weight: 700; }
    .severity-low      { color: #16a34a; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar for API Key ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    st.markdown("[Get Free API Key Here](https://aistudio.google.com/)")
    if api_key:
        genai.configure(api_key=api_key)

# ─── Session State Init ────────────────────────────────────────────────────────
if "bug_history"      not in st.session_state: st.session_state.bug_history      = []
if "chat_messages"    not in st.session_state: st.session_state.chat_messages    = []
if "debate_results"   not in st.session_state: st.session_state.debate_results   = []
if "last_bug_context" not in st.session_state: st.session_state.last_bug_context = ""

# ─── Helper: Clean JSON ────────────────────────────────────────────────────────
def clean_json(raw_text: str) -> str:
    """Removes markdown code blocks if Gemini returns them around JSON."""
    return re.sub(r'