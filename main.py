import streamlit as st
import json
import re
import requests
from datetime import datetime

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Bug Investigation Agent", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 8px; }
    .feature-badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 12px; font-weight: 600; margin-bottom: 6px;
    }
    .badge-core { background: #dbeafe; color: #1e40af; }
    .badge-adv  { background: #fef3c7; color: #92400e; }
    .badge-pro  { background: #fee2e2; color: #991b1b; }
    .result-box {
        background: #f8fafc; border-left: 4px solid #6366f1;
        border-radius: 8px; padding: 16px; margin: 12px 0;
    }
    .severity-critical { color: #dc2626; font-weight: 700; }
    .severity-high     { color: #ea580c; font-weight: 700; }
    .severity-medium   { color: #ca8a04; font-weight: 700; }
    .severity-low      { color: #16a34a; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")
    st.success("✅ AI model ready — no API key required!")
    st.markdown("**Model:** Claude claude-haiku-4-5-20251001 (Anthropic)")
    st.markdown("---")
    st.caption("v2.0 — AI Bug Investigation Agent")

# ─── Session State ─────────────────────────────────────────────────────────────
for key, default in [("bug_history", []), ("chat_messages", []),
                     ("debate_results", []), ("last_bug_context", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Constants ─────────────────────────────────────────────────────────────────
SEV_CSS   = {"Critical": "severity-critical", "High": "severity-high",
             "Medium": "severity-medium",     "Low":  "severity-low"}
SEV_COLOR = {"Critical": "#dc2626", "High": "#ea580c",
             "Medium":   "#ca8a04", "Low":  "#16a34a"}
LANG_MAP  = {"Python": "python", "JavaScript": "javascript",
             "Java": "java",     "Go": "go", "C#": "csharp"}

# ─── Helpers ───────────────────────────────────────────────────────────────────
def clean_json(raw: str) -> str:
    return re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

def result_box(html: str, border_color: str = "#6366f1") -> None:
    st.markdown(
        f'<div class="result-box" style="border-left-color:{border_color}">{html}</div>',
        unsafe_allow_html=True,
    )

def badge(tier: str) -> None:
    cls = {"Core": "badge-core", "Advanced": "badge-adv", "Pro": "badge-pro"}.get(tier, "")
    st.markdown(f'<span class="feature-badge {cls}">{tier}</span>', unsafe_allow_html=True)

def call_claude(system_prompt: str, user_message: str) -> str:
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1500,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=60,
        )
        data = resp.json()
        if "content" in data and data["content"]:
            return data["content"][0].get("text", "")
        return f"API Error: {data.get('error', {}).get('message', str(data))}"
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Please try again."
    except Exception as e:
        return f"Error: {e}"

def call_claude_json(system_prompt: str, user_message: str, fallback: dict | list) -> dict | list:
    raw = call_claude(system_prompt, user_message)
    try:
        return json.loads(clean_json(raw))
    except Exception:
        if isinstance(fallback, dict):
            # inject the raw text into the first string-valued key as a fallback message
            return {**fallback, next(iter(fallback)): raw}
        return fallback

# ─── Core Features ─────────────────────────────────────────────────────────────
def analyze_stack_trace(stack_trace: str, lang: str) -> dict:
    system = f"""You are an expert {lang} debugger. Analyze the given stack trace / error log.
Return ONLY a JSON object with keys: error_type (string), root_cause (string, 1-2 sentences),
affected_files (list of strings), fix_suggestion (string), confidence (number 0-100). No markdown."""
    return call_claude_json(system, stack_trace,
        {"error_type": "Unknown", "root_cause": "", "affected_files": [], "fix_suggestion": "", "confidence": 50})

def save_to_history(bug_desc: str, result: str) -> None:
    st.session_state.bug_history.append({
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "description":    bug_desc[:80] + ("..." if len(bug_desc) > 80 else ""),
        "result_summary": result[:200],
    })

def find_similar_bugs(current_bug: str) -> list:
    if not st.session_state.bug_history:
        return []
    history_text = "\n".join(f"[{h['timestamp']}] {h['description']}"
                             for h in st.session_state.bug_history)
    system = """You are a bug similarity matcher. Given a new bug and a list of past bugs,
return ONLY a JSON array of objects with keys: index (int, 0-based), similarity_score (0-100),
reason (string). Only include bugs with score > 40. No markdown."""
    return call_claude_json(system, f"New bug: {current_bug}\n\nPast bugs:\n{history_text}", [])

def analyze_git_diff(diff_text: str, bug_desc: str) -> str:
    system = """You are a senior code reviewer. Analyze the git diff and identify which changes
most likely introduced the reported bug. Be specific about file names, line numbers, and logic errors."""
    return call_claude(system, f"Bug reported: {bug_desc}\n\nGit Diff:\n{diff_text}")

# ─── Advanced Features ─────────────────────────────────────────────────────────
def generate_hypotheses(bug_desc: str, extra_context: str = "") -> list:
    system = """You are a systematic debugging expert. Generate exactly 4 distinct hypotheses
for the given bug. Return ONLY a JSON array where each item has: hypothesis (string),
confidence (number 0-100), evidence_needed (string), quick_test (string, one-liner).
Sort by confidence descending. No markdown."""
    return call_claude_json(system, f"Bug: {bug_desc}\nExtra context: {extra_context}", [])

def suggest_debug_commands(bug_desc: str, tech_stack: str) -> list:
    system = f"""You are a DevOps/backend expert for {tech_stack}. Suggest debugging commands.
Return ONLY a JSON array where each item has: command (string), purpose (string),
category (one of [logs, env, network, db, process]). No markdown."""
    return call_claude_json(system, bug_desc, [])

def generate_test_case(bug_desc: str, language: str) -> str:
    system = f"""You are a {language} test engineer. Write a minimal unit test that reproduces
the described bug. Include setup, the failing assertion, and a comment explaining what should be fixed.
Return only the code, no explanation."""
    return call_claude(system, bug_desc)

def classify_severity(bug_desc: str) -> dict:
    system = """Classify the severity of this bug. Return ONLY JSON with keys:
severity (one of [Critical, High, Medium, Low]), impact (string), affected_users (string estimate),
urgency (string), reasoning (string). No markdown."""
    return call_claude_json(system, bug_desc,
        {"severity": "Unknown", "impact": "", "affected_users": "?", "urgency": "?", "reasoning": ""})

# ─── Pro Features ───────────────────────────────────────────────────────────────
def analyze_log_anomalies(log_text: str) -> dict:
    system = """You are a log analysis expert. Detect anomalies, errors, warnings, and patterns
in the provided logs. Return ONLY JSON with keys: anomalies (list of {line, issue, severity}),
error_count (int), warning_count (int), patterns (list of strings), summary (string). No markdown."""
    return call_claude_json(system, log_text,
        {"anomalies": [], "error_count": 0, "warning_count": 0, "patterns": [], "summary": ""})

def run_multi_agent_debate(bug_desc: str) -> tuple[list, dict]:
    agents = [
        ("Network Agent", "You believe most bugs are network/API related. Argue why this is a network issue."),
        ("DB Agent",      "You believe most bugs are database/query related. Argue why this is a DB issue."),
        ("Logic Agent",   "You believe most bugs are business logic/code errors. Argue why this is a code logic issue."),
        ("Config Agent",  "You believe most bugs are environment/config problems. Argue why this is a config/env issue."),
    ]
    results = []
    for name, persona in agents:
        system = f"""{persona}
Give a 3-sentence argument. Then rate your own confidence 0-100.
Return ONLY JSON: {{"argument": "...", "confidence": 80, "key_evidence": "..."}}"""
        data = call_claude_json(system, f"Bug: {bug_desc}",
                                {"argument": "Parse error", "confidence": 0, "key_evidence": ""})
        data["agent"] = name
        results.append(data)

    debate_summary = "\n".join(
        f"{r['agent']}: {r['argument']} (confidence: {r['confidence']})" for r in results
    )
    judge_system = """You are an impartial judge. Given arguments from 4 agents, pick the most likely cause.
Return ONLY JSON: {"winner": "agent name", "reasoning": "...", "final_verdict": "..."}"""
    verdict = call_claude_json(judge_system, debate_summary,
                               {"winner": "Unknown", "reasoning": "", "final_verdict": ""})
    return results, verdict

def generate_bug_report(bug_desc: str, analysis: str, severity: str, format_type: str) -> str:
    system = f"""You are a technical writer. Generate a professional {format_type} bug report.
Include: Title, Description, Steps to Reproduce, Expected vs Actual, Severity, Root Cause,
Fix Suggestion, Labels/Tags. Use {format_type} formatting
(Markdown for GitHub, plain structured text for Jira)."""
    return call_claude(system, f"Bug: {bug_desc}\nAnalysis: {analysis}\nSeverity: {severity}")

def chat_with_agent(user_message: str, bug_context: str) -> str:
    system = f"""You are an expert AI Bug Investigation Agent. You have the following bug context:
{bug_context}
Help the user investigate and resolve their bug. Be precise, technical, and actionable."""
    history = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in st.session_state.chat_messages[-10:]
    )
    return call_claude(system, f"{history}\nUser: {user_message}")

# ═══════════════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════════════
st.title("🔍 AI Bug Investigation Agent")
st.caption("Powered by Anthropic Claude — Stack traces, git diffs, hypotheses, debates, aur zyada")

tabs = st.tabs([
    "🏠 Main", "📋 Stack Trace", "🌿 Git Diff", "🧠 Hypotheses",
    "⚙️ Debug Cmds", "🧪 Test Gen", "📊 Severity",
    "📜 Log Watcher", "⚔️ Agent Debate", "📝 Bug Report", "💬 Chat", "🗂️ History",
])
(tab_main, tab_stack, tab_git, tab_hypo, tab_cmds,
 tab_test, tab_sev, tab_log, tab_debate, tab_report,
 tab_chat, tab_hist) = tabs

# ─── Main ─────────────────────────────────────────────────────────────────────
with tab_main:
    badge("Core")
    st.subheader("Describe your bug")
    user_input = st.text_area("Bug description:", height=120,
        placeholder="e.g. App crashes with NullPointerException when user submits login form on mobile...")
    st.selectbox("Language / Framework",
        ["Python", "JavaScript", "Java", "Go", "C#", "Ruby", "PHP", "Other"])

    if st.button("🔍 Investigate Bug", type="primary", use_container_width=True):
        if not user_input.strip():
            st.warning("Please enter a bug description.")
        else:
            st.session_state.last_bug_context = user_input
            with st.spinner("Analyzing severity..."):
                sev_result = classify_severity(user_input)
            sev = sev_result.get("severity", "?")
            result_box(f"""<b>Severity:</b> <span class="{SEV_CSS.get(sev, '')}">{sev}</span><br>
<b>Impact:</b> {sev_result.get('impact', '')}<br>
<b>Affected Users:</b> {sev_result.get('affected_users', '')}<br>
<b>Reasoning:</b> {sev_result.get('reasoning', '')}""")

            with st.spinner("Generating hypotheses..."):
                hypotheses = generate_hypotheses(user_input)
            if hypotheses:
                st.subheader("🧠 Top Hypotheses")
                for i, h in enumerate(hypotheses[:4], 1):
                    with st.expander(f"#{i} — {h.get('hypothesis', '')[:60]}  ({h.get('confidence', 0)}% confidence)"):
                        st.write(f"**Evidence needed:** {h.get('evidence_needed', '')}")
                        st.code(h.get("quick_test", ""), language="bash")

            with st.spinner("Checking similar past bugs..."):
                similar = find_similar_bugs(user_input)
            if similar:
                st.subheader("📚 Similar Past Bugs")
                for s in similar:
                    idx = s.get("index", 0)
                    if idx < len(st.session_state.bug_history):
                        st.info(f"**[{s.get('similarity_score')}% match]** "
                                f"{st.session_state.bug_history[idx]['description']} — {s.get('reason', '')}")

            save_to_history(user_input, str(sev_result))
            st.success("✅ Investigation complete! Check other tabs for detailed analysis.")

# ─── Stack Trace ──────────────────────────────────────────────────────────────
with tab_stack:
    badge("Core")
    st.subheader("Stack Trace Analyzer")
    st.caption("Error log ya stack trace paste karo — root cause nikalta hai")
    stack_lang  = st.selectbox("Language", ["Python", "JavaScript", "Java", "Go", "C#", "Other"], key="stack_lang")
    stack_input = st.text_area("Paste stack trace / error log:", height=200,
        placeholder="Traceback (most recent call last):\n  File ...\nNullPointerException: ...")
    if st.button("Analyze Stack Trace", use_container_width=True):
        if not stack_input.strip():
            st.warning("Please paste a stack trace.")
        else:
            with st.spinner("Analyzing..."):
                result = analyze_stack_trace(stack_input, stack_lang)
            result_box(f"""<b>Error Type:</b> {result.get('error_type', '')}<br>
<b>Root Cause:</b> {result.get('root_cause', '')}<br>
<b>Confidence:</b> {result.get('confidence', 0)}%""")
            if result.get("affected_files"):
                st.write("**Affected Files:**", ", ".join(result["affected_files"]))
            if result.get("fix_suggestion"):
                st.success(f"**Fix Suggestion:** {result['fix_suggestion']}")
            save_to_history(stack_input[:100], result.get("root_cause", ""))

# ─── Git Diff ─────────────────────────────────────────────────────────────────
with tab_git:
    badge("Core")
    st.subheader("Git Diff Analyzer")
    st.caption("Recent commit diff paste karo — kaunse change ne bug introduce kiya?")
    git_bug_desc = st.text_input("Bug description (optional):", key="git_bug")
    diff_input   = st.text_area("Paste git diff output:", height=250,
        placeholder="diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ ...")
    if st.button("Analyze Diff", use_container_width=True):
        if not diff_input.strip():
            st.warning("Please paste a git diff.")
        else:
            with st.spinner("Scanning diff for bug source..."):
                result = analyze_git_diff(diff_input, git_bug_desc or "Unknown bug")
            result_box(result)

# ─── Hypotheses ───────────────────────────────────────────────────────────────
with tab_hypo:
    badge("Advanced")
    st.subheader("Hypothesis Engine")
    st.caption("4 alag theories generate karta hai confidence score ke saath")
    hypo_bug   = st.text_area("Bug description:", height=100, key="hypo_bug",
        value=st.session_state.last_bug_context)
    hypo_extra = st.text_input("Extra context (optional):",
        placeholder="e.g. only happens in production, after deploy v2.3")
    if st.button("Generate Hypotheses", use_container_width=True):
        if not hypo_bug.strip():
            st.warning("Please enter a bug description.")
        else:
            with st.spinner("Generating 4 hypotheses..."):
                hypotheses = generate_hypotheses(hypo_bug, hypo_extra)
            for i, h in enumerate(hypotheses, 1):
                conf  = h.get("confidence", 0)
                color = "#dc2626" if conf >= 75 else "#ca8a04" if conf >= 50 else "#16a34a"
                result_box(f"""<b>Hypothesis #{i}:</b> {h.get('hypothesis', '')}<br>
<b>Confidence:</b> <span style="color:{color};font-weight:700">{conf}%</span><br>
<b>Evidence needed:</b> {h.get('evidence_needed', '')}<br>
<b>Quick test:</b> <code>{h.get('quick_test', '')}</code>""")

# ─── Debug Commands ───────────────────────────────────────────────────────────
with tab_cmds:
    badge("Advanced")
    st.subheader("Auto Debug Commands")
    st.caption("Kaunse commands run kare? Agent suggest karega purpose ke saath")
    cmd_bug   = st.text_area("Bug description:", height=80, key="cmd_bug",
        value=st.session_state.last_bug_context)
    cmd_stack = st.text_input("Tech stack:", placeholder="e.g. Django + PostgreSQL + Redis")
    if st.button("Suggest Commands", use_container_width=True):
        if not cmd_bug.strip():
            st.warning("Please enter a bug description.")
        else:
            with st.spinner("Building debug command list..."):
                commands = suggest_debug_commands(cmd_bug, cmd_stack or "general")
            cat_icons = {"logs": "📋", "env": "🌿", "network": "🌐", "db": "🗄️", "process": "⚙️"}
            for cmd in commands:
                st.markdown(f"**{cat_icons.get(cmd.get('category', ''), '🔧')} {cmd.get('purpose', '')}**")
                st.code(cmd.get("command", ""), language="bash")

# ─── Test Generator ───────────────────────────────────────────────────────────
with tab_test:
    badge("Advanced")
    st.subheader("Test Case Generator")
    st.caption("Bug reproduce karne wala minimal unit test likhta hai")
    test_bug  = st.text_area("Bug description:", height=80, key="test_bug",
        value=st.session_state.last_bug_context)
    test_lang = st.selectbox("Language", ["Python", "JavaScript", "Java", "Go", "C#"], key="test_lang2")
    if st.button("Generate Test Case", use_container_width=True):
        if not test_bug.strip():
            st.warning("Please enter a bug description.")
        else:
            with st.spinner("Writing test case..."):
                test_code = generate_test_case(test_bug, test_lang)
            st.code(test_code, language=LANG_MAP.get(test_lang, "python"))
            st.download_button("⬇️ Download test file", test_code,
                               file_name=f"test_bug_{datetime.now().strftime('%H%M%S')}.py")

# ─── Severity ─────────────────────────────────────────────────────────────────
with tab_sev:
    badge("Advanced")
    st.subheader("Severity Classifier")
    st.caption("Bug ka impact aur urgency classify karta hai")
    sev_bug = st.text_area("Bug description:", height=100, key="sev_bug",
        value=st.session_state.last_bug_context)
    if st.button("Classify Severity", use_container_width=True):
        if not sev_bug.strip():
            st.warning("Please enter a bug description.")
        else:
            with st.spinner("Classifying..."):
                result = classify_severity(sev_bug)
            sev   = result.get("severity", "?")
            color = SEV_COLOR.get(sev, "#6b7280")
            result_box(f"""<h2 style="color:{color};margin:0">{sev}</h2>
<b>Impact:</b> {result.get('impact', '')}<br>
<b>Affected Users:</b> {result.get('affected_users', '')}<br>
<b>Urgency:</b> {result.get('urgency', '')}<br>
<b>Reasoning:</b> {result.get('reasoning', '')}""")

# ─── Log Watcher ──────────────────────────────────────────────────────────────
with tab_log:
    badge("Pro")
    st.subheader("Log Watcher & Anomaly Detector")
    st.caption("Logs paste karo — errors, warnings, aur patterns detect karta hai")
    log_input = st.text_area("Paste your logs here:", height=250,
        placeholder="2024-01-15 10:23:45 INFO  Starting server...\n2024-01-15 10:23:46 ERROR DB connection failed\n...")
    if st.button("🔎 Analyze Logs", use_container_width=True):
        if not log_input.strip():
            st.warning("Please paste some log content.")
        else:
            with st.spinner("Scanning logs for anomalies..."):
                result = analyze_log_anomalies(log_input)
            col1, col2, col3 = st.columns(3)
            col1.metric("Anomalies Found", len(result.get("anomalies", [])))
            col2.metric("Errors",          result.get("error_count", 0))
            col3.metric("Warnings",        result.get("warning_count", 0))
            st.write("**Summary:**", result.get("summary", ""))
            if result.get("patterns"):
                st.write("**Patterns Detected:**")
                for p in result["patterns"]:
                    st.info(p)
            if result.get("anomalies"):
                st.write("**Anomalies:**")
                for a in result["anomalies"]:
                    icon = "🔴" if a.get("severity", "").lower() == "error" else "🟡"
                    st.markdown(f"{icon} **{a.get('issue', '')}** → `{a.get('line', '')[:80]}`")

# ─── Agent Debate ─────────────────────────────────────────────────────────────
with tab_debate:
    badge("Pro")
    st.subheader("Multi-Agent Debate")
    st.caption("4 alag agents bug ke liye argue karte hain — judge decide karta hai winner")
    st.warning("⏱️ Yeh feature 4 API calls karta hai — thoda time lagega (~20s)")
    debate_bug = st.text_area("Bug description:", height=100, key="debate_bug",
        value=st.session_state.last_bug_context)
    if st.button("⚔️ Start Debate", use_container_width=True):
        if not debate_bug.strip():
            st.warning("Please enter a bug description.")
        else:
            with st.spinner("4 agents debate kar rahe hain..."):
                results, verdict = run_multi_agent_debate(debate_bug)
            agent_icons = {"Network Agent": "🌐", "DB Agent": "🗄️", "Logic Agent": "🧠", "Config Agent": "⚙️"}
            cols = st.columns(2)
            for i, r in enumerate(results):
                with cols[i % 2]:
                    icon  = agent_icons.get(r["agent"], "🤖")
                    color = "#dc2626" if r["confidence"] >= 70 else "#ca8a04" if r["confidence"] >= 40 else "#6b7280"
                    result_box(f"""<b>{icon} {r['agent']}</b> — <span style="color:{color};font-weight:700">{r['confidence']}%</span><br>
{r.get('argument', '')}<br>
<small><b>Key evidence:</b> {r.get('key_evidence', '')}</small>""")
            st.markdown("---")
            result_box(f"""<b>⚖️ VERDICT — Winner: {verdict.get('winner', '?')}</b><br>
{verdict.get('reasoning', '')}<br><br>
<b>Final conclusion:</b> {verdict.get('final_verdict', '')}""", border_color="#16a34a")

# ─── Bug Report ───────────────────────────────────────────────────────────────
with tab_report:
    badge("Pro")
    st.subheader("Bug Report Writer")
    st.caption("Professional GitHub/Jira-ready bug report auto-generate karta hai")
    rep_bug      = st.text_area("Bug description:", height=80, key="rep_bug",
        value=st.session_state.last_bug_context)
    rep_analysis = st.text_area("Analysis / findings (optional):", height=80,
        placeholder="Root cause, affected files, etc.")
    col1, col2   = st.columns(2)
    with col1: rep_sev    = st.selectbox("Severity", ["Critical", "High", "Medium", "Low"])
    with col2: rep_format = st.selectbox("Format",   ["GitHub Markdown", "Jira Plain Text"])
    if st.button("📝 Generate Report", use_container_width=True):
        if not rep_bug.strip():
            st.warning("Please enter a bug description.")
        else:
            with st.spinner("Writing bug report..."):
                report = generate_bug_report(rep_bug, rep_analysis, rep_sev, rep_format)
            st.markdown(report)
            st.download_button("⬇️ Download Report", report,
                               file_name=f"bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

# ─── Chat ─────────────────────────────────────────────────────────────────────
with tab_chat:
    badge("Pro")
    st.subheader("Chat with Bug Agent")
    st.caption("Bug context ke saath interactive conversation")
    chat_ctx = st.text_area("Bug context (auto-filled from Main tab):",
        value=st.session_state.last_bug_context, height=60, key="chat_ctx")
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if prompt := st.chat_input("Ask something about your bug..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = chat_with_agent(prompt, chat_ctx)
            st.write(reply)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()

# ─── History ──────────────────────────────────────────────────────────────────
with tab_hist:
    badge("Core")
    st.subheader("Bug History & Memory")
    st.caption("Is session mein investigate kiye gaye saare bugs")
    if not st.session_state.bug_history:
        st.info("Abhi koi bug investigate nahi kiya. Main tab se start karo!")
    else:
        for bug in reversed(st.session_state.bug_history):
            with st.expander(f"[{bug['timestamp']}] {bug['description']}"):
                st.write(bug["result_summary"])
        if st.button("🗑️ Clear History"):
            st.session_state.bug_history = []
            st.rerun()
