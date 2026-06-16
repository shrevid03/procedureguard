"""ProcedureGuard — Cinematic Compliance Dashboard v4"""
import json, os, math
from collections import defaultdict
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    AZURE_OK = True
except ImportError:
    AZURE_OK = False

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

st.set_page_config(page_title="ProcedureGuard", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg:          #F2EBDD;   /* cream */
  --s1:          #FBF7EE;   /* bone surface */
  --s2:          #F6F0E2;
  --s3:          #EFE7D6;
  --s4:          #E8DEC9;   /* deepest inset / empty cell */
  --border:      #E2D6BF;   /* warm border */
  --border-2:    #D4C4A6;
  --text:        #3D3528;   /* espresso */
  --mid:         #6E6151;   /* muted brown */
  --dim:         #A0917A;   /* taupe */
  --accent:      #C8694B;   /* terracotta */
  --accent-glow: rgba(200,105,75,0.18);
  --pass:        #7A8C52;   /* olive */
  --pass-bg:     rgba(122,140,82,0.10);
  --fail:        #C8694B;   /* terracotta */
  --fail-bg:     rgba(200,105,75,0.10);
  --warn:        #C2913C;   /* ochre */
  --warn-bg:     rgba(194,145,60,0.10);
  --hold:        #B0A48C;   /* sand */
  --font:        'DM Sans', system-ui, sans-serif;
  --mono:        'JetBrains Mono', 'SF Mono', monospace;
  --display:     'Bricolage Grotesque', sans-serif;
  --r:           8px;
  --r-sm:        5px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── App shell ──────────────────────────────────────── */
.stApp {
  background-color: var(--bg);
  background-image:
    radial-gradient(circle, var(--border) 1px, transparent 1px);
  background-size: 26px 26px;
  font-family: var(--font);
}

/* hide all streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"],
div[data-testid="stToolbar"], div[data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 0 !important; max-width: 1480px !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; }

/* ── Sidebar ────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: var(--s1) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] * { color: var(--text) !important; font-family: var(--font) !important; }

/* ── Typography ─────────────────────────────────────── */
h1,h2,h3 { color: var(--text) !important; font-family: var(--display) !important; font-weight: 600 !important; letter-spacing: -0.015em; }
div[data-testid="stMarkdownContainer"] p { color: var(--mid); font-family: var(--font); }
p { font-family: var(--font); }

/* ── Scrollbar ──────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--s1); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--dim); }

/* ── Animations ─────────────────────────────────────── */
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}
@keyframes fade-up {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes sweep {
  from { transform: translateX(-100%); opacity: 0; }
  60%  { opacity: 1; }
  to   { transform: translateX(400%); opacity: 0; }
}

/* ── Brand ──────────────────────────────────────────── */
.pg-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 20px 16px 16px; border-bottom: 1px solid var(--border);
}
.pg-mark {
  width: 32px; height: 32px; border-radius: 7px; flex-shrink: 0;
  background: linear-gradient(135deg, #C8694B 0%, #C2913C 100%);
  display: flex; align-items: center; justify-content: center;
}
.pg-mark svg { width: 16px; height: 16px; }
.pg-name { font-size: 14px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; line-height: 1.2; }
.pg-tag  { font-size: 8.5px; color: var(--dim); text-transform: uppercase; letter-spacing: 2px; font-family: var(--mono); margin-top: 2px; }

/* ── Sidebar nav ────────────────────────────────────── */
.pg-nav-section { padding: 12px 16px 6px; font-size: 8.5px; color: var(--dim); text-transform: uppercase; letter-spacing: 2px; font-family: var(--mono); }
.stRadio > div { gap: 0 !important; padding: 0 8px; }
.stRadio label { padding: 9px 12px !important; border-radius: var(--r-sm) !important; margin: 1px 0 !important; font-size: 13px !important; color: var(--mid) !important; transition: all 0.15s; }
.stRadio label:hover { background: var(--s2) !important; color: var(--text) !important; }
.stRadio [data-baseweb="radio"] { display: none !important; }

/* ── Sidebar meta ───────────────────────────────────── */
.pg-sb-block { padding: 0 16px; }
.pg-sb-hdr { font-size: 8.5px; color: var(--dim); text-transform: uppercase; letter-spacing: 2px; font-family: var(--mono); margin-bottom: 10px; }
.pg-sb-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--border); }
.pg-sb-row:last-child { border-bottom: none; }
.pg-sb-k { font-size: 11px; color: var(--mid); }
.pg-sb-v { font-size: 11px; color: var(--text); font-family: var(--mono); font-weight: 500; }
.pg-sb-div { border-top: 1px solid var(--border); margin: 14px 0; }

/* ── Top run bar ────────────────────────────────────── */
.pg-topbar {
  background: var(--s1); border-bottom: 1px solid var(--border);
  padding: 12px 24px; margin: 0 -1.5rem 24px;
  display: flex; align-items: center; gap: 0; overflow: hidden; position: relative;
}
.pg-topbar::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--accent) 40%, var(--pass) 70%, transparent 100%);
  opacity: 0.6;
}
.pg-topbar-title { font-size: 14px; font-weight: 600; color: var(--text); letter-spacing: -0.01em; }
.pg-topbar-sub { font-size: 11px; color: var(--dim); font-family: var(--mono); margin-top: 2px; }
.pg-topbar-divider { width: 1px; background: var(--border); height: 30px; margin: 0 24px; flex-shrink: 0; }
.pg-topbar-meta { display: flex; flex-direction: column; gap: 2px; }
.pg-topbar-mk { font-size: 8.5px; color: var(--dim); text-transform: uppercase; letter-spacing: 1.8px; font-family: var(--mono); }
.pg-topbar-mv { font-size: 12px; color: var(--text); font-family: var(--mono); font-weight: 500; }
.pg-mode-live {
  display: flex; align-items: center; gap: 7px;
  background: var(--pass-bg); border: 1px solid rgba(122,140,82,0.28);
  border-radius: 20px; padding: 4px 12px; margin-left: auto;
}
.pg-mode-mock {
  display: flex; align-items: center; gap: 7px;
  background: var(--warn-bg); border: 1px solid rgba(194,145,60,0.28);
  border-radius: 20px; padding: 4px 12px; margin-left: auto;
}
.pg-mode-dot {
  width: 6px; height: 6px; border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}
.pg-mode-live .pg-mode-dot { background: var(--pass); }
.pg-mode-mock .pg-mode-dot { background: var(--warn); }
.pg-mode-label { font-size: 10.5px; font-weight: 600; font-family: var(--mono); text-transform: uppercase; letter-spacing: 1.5px; }
.pg-mode-live .pg-mode-label { color: var(--pass); }
.pg-mode-mock .pg-mode-label { color: var(--warn); }

/* ── Hero score ─────────────────────────────────────── */
.pg-hero-wrap {
  background: var(--s1); border: 1px solid var(--border); border-radius: 12px;
  padding: 32px 36px; margin-bottom: 16px; position: relative; overflow: hidden;
  animation: fade-up 0.4s ease both;
}
.pg-hero-wrap::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.5;
}
.pg-score-eyebrow { font-size: 9px; color: var(--dim); text-transform: uppercase; letter-spacing: 3px; font-family: var(--mono); margin-bottom: 12px; }
.pg-score-number {
  font-size: 96px; font-weight: 700; color: var(--text); line-height: 1;
  letter-spacing: -0.04em; position: relative; display: inline-block; font-family: var(--display);
}
.pg-score-number .pg-score-pct { font-size: 40px; color: var(--mid); vertical-align: super; margin-left: 4px; }
.pg-score-sweep {
  position: absolute; top: 0; left: 0; bottom: 0; width: 40%;
  background: linear-gradient(90deg, transparent, rgba(200,105,75,0.07), transparent);
  animation: sweep 3s ease-in-out 0.5s both;
}
.pg-score-bar-wrap { margin-top: 18px; }
.pg-score-bar-track { background: var(--s3); border-radius: 4px; height: 4px; width: 100%; }
.pg-score-bar-fill { height: 4px; border-radius: 4px; transition: width 1s ease; }
.pg-score-threshold {
  display: flex; align-items: center; gap: 6px; margin-top: 10px;
}
.pg-score-thr-line { font-size: 10px; color: var(--dim); font-family: var(--mono); }
.pg-score-thr-val { color: var(--accent); font-weight: 500; }

/* ── Verdict ────────────────────────────────────────── */
.pg-verdict {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px 18px; border-radius: var(--r); margin-top: 20px;
  border-left: 2px solid;
}
.pg-verdict.pass { background: var(--pass-bg); border-left-color: var(--pass); }
.pg-verdict.fail { background: var(--fail-bg); border-left-color: var(--fail); }
.pg-verdict.hold { background: var(--warn-bg); border-left-color: var(--warn); }
.pg-v-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.pg-verdict.pass .pg-v-dot { background: var(--pass); animation: pulse-dot 2.5s ease infinite; }
.pg-verdict.fail .pg-v-dot { background: var(--fail); }
.pg-verdict.hold .pg-v-dot { background: var(--warn); animation: pulse-dot 2.5s ease infinite; }
.pg-v-title { font-size: 11px; font-weight: 600; color: var(--text); text-transform: uppercase; letter-spacing: 2px; font-family: var(--mono); }
.pg-v-msg { font-size: 13px; color: var(--mid); margin-top: 4px; line-height: 1.5; }

/* ── Metric cards ───────────────────────────────────── */
.pg-metric {
  background: var(--s1); border: 1px solid var(--border); border-radius: var(--r);
  padding: 20px 22px; animation: fade-up 0.4s ease both; position: relative; overflow: hidden;
}
.pg-metric::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
}
.pg-metric.pass::after { background: var(--pass); }
.pg-metric.fail::after { background: var(--fail); }
.pg-metric.warn::after { background: var(--warn); }
.pg-metric.info::after { background: var(--accent); }
.pg-metric-label { font-size: 9px; color: var(--dim); text-transform: uppercase; letter-spacing: 2.5px; font-family: var(--mono); }
.pg-metric-val { font-size: 44px; font-weight: 600; color: var(--text); letter-spacing: -0.03em; line-height: 1; margin: 8px 0 12px; font-family: var(--display); }
.pg-metric-bar-track { background: var(--s3); border-radius: 3px; height: 3px; }
.pg-metric-bar-fill { height: 3px; border-radius: 3px; }
.pg-metric.pass .pg-metric-bar-fill { background: var(--pass); }
.pg-metric.fail .pg-metric-bar-fill { background: var(--fail); }
.pg-metric.warn .pg-metric-bar-fill { background: var(--warn); }
.pg-metric.info .pg-metric-bar-fill { background: var(--accent); }
.pg-metric-sub { font-size: 10.5px; color: var(--dim); font-family: var(--mono); margin-top: 8px; }

/* ── Section headers ────────────────────────────────── */
.pg-section {
  display: flex; align-items: center; justify-content: space-between;
  margin: 28px 0 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border);
}
.pg-section-label { font-size: 9.5px; font-weight: 600; color: var(--dim); text-transform: uppercase; letter-spacing: 2.5px; font-family: var(--mono); }
.pg-section-badge { font-size: 9.5px; color: var(--mid); background: var(--s2); padding: 3px 10px; border-radius: 20px; border: 1px solid var(--border); font-family: var(--mono); }

/* ── Chart panels ───────────────────────────────────── */
.pg-panel {
  background: var(--s1); border: 1px solid var(--border); border-radius: var(--r);
  padding: 20px 22px; height: 100%; animation: fade-up 0.5s ease 0.1s both;
}
.pg-panel-title { font-size: 10px; font-weight: 600; color: var(--dim); text-transform: uppercase; letter-spacing: 2.5px; font-family: var(--mono); margin-bottom: 16px; }

/* ── Compliance matrix ──────────────────────────────── */
.pg-matrix {
  display: flex; flex-wrap: wrap; gap: 4px; padding-top: 4px;
}
.pg-cell {
  width: 22px; height: 22px; border-radius: 4px; position: relative; cursor: default;
  transition: transform 0.1s, opacity 0.1s; flex-shrink: 0;
}
.pg-cell:hover { transform: scale(1.3); z-index: 10; opacity: 1 !important; }
.pg-cell-pass  { background: var(--pass); opacity: 0.75; }
.pg-cell-fail  { background: var(--fail); opacity: 0.85; }
.pg-cell-warn  { background: var(--warn); opacity: 0.70; }
.pg-cell-hold  { background: var(--s4); border: 1px solid var(--border); opacity: 0.60; }
.pg-matrix-legend { display: flex; gap: 16px; margin-top: 14px; flex-wrap: wrap; }
.pg-legend-item { display: flex; align-items: center; gap: 6px; }
.pg-legend-dot { width: 8px; height: 8px; border-radius: 2px; }
.pg-legend-label { font-size: 10px; color: var(--mid); font-family: var(--mono); }

/* ── Deviation cards ────────────────────────────────── */
.pg-dev {
  background: var(--s1); border: 1px solid var(--border); border-radius: var(--r);
  padding: 14px 18px; margin-bottom: 8px;
  display: grid; grid-template-columns: 78px 1fr auto;
  gap: 16px; align-items: center; transition: border-color 0.15s;
}
.pg-dev:hover { border-color: var(--border-2); }
.pg-dev-ts { font-family: var(--mono); color: var(--warn); font-size: 11px; font-weight: 500; display: flex; flex-direction: column; gap: 2px; }
.pg-dev-ts-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--warn); margin-bottom: 4px; }
.pg-dev-step { color: var(--text); font-weight: 600; font-size: 13px; }
.pg-dev-action { color: var(--mid); font-size: 12px; margin-top: 2px; line-height: 1.4; }
.pg-dev-conf { font-family: var(--mono); font-size: 10px; color: var(--mid); background: var(--s3); padding: 5px 10px; border-radius: 5px; border: 1px solid var(--border); white-space: nowrap; }

/* ── Checklist ──────────────────────────────────────── */
.pg-chapter-hdr {
  font-size: 9.5px; font-weight: 600; color: var(--accent); text-transform: uppercase;
  letter-spacing: 2.5px; margin: 24px 0 8px; padding-bottom: 8px;
  border-bottom: 1px solid var(--border); font-family: var(--mono);
}
.pg-rule {
  background: var(--s1); border: 1px solid var(--border); border-left: 2px solid;
  border-radius: var(--r); padding: 11px 16px; margin-bottom: 6px; transition: border-color 0.15s;
}
.pg-rule:hover { border-color: var(--border-2); }
.pg-rule.pass { border-left-color: var(--pass); }
.pg-rule.fail { border-left-color: var(--fail); }
.pg-rule.warn { border-left-color: var(--warn); }
.pg-rule.hold { border-left-color: var(--hold); }
.pg-rule-hdr { display: flex; justify-content: space-between; align-items: center; }
.pg-rule-id { font-family: var(--mono); font-size: 10.5px; color: var(--accent); font-weight: 500; }
.pg-rule-badge { font-size: 8.5px; font-weight: 600; padding: 3px 9px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.8px; font-family: var(--mono); }
.pg-rule-badge.pass { background: rgba(122,140,82,0.15); color: var(--pass); }
.pg-rule-badge.fail { background: rgba(200,105,75,0.15); color: var(--fail); }
.pg-rule-badge.warn { background: rgba(194,145,60,0.15); color: var(--warn); }
.pg-rule-badge.hold { background: rgba(60,69,96,0.25); color: var(--mid); }
.pg-rule-action { color: var(--mid); font-size: 12.5px; margin-top: 6px; line-height: 1.5; }

/* ── Chat / SOP ─────────────────────────────────────── */
.stChatMessage { background: var(--s2) !important; border: 1px solid var(--border) !important; border-radius: var(--r) !important; }
details { background: var(--s1); border: 1px solid var(--border); border-radius: var(--r); padding: 8px 14px; margin-bottom: 6px; }
details summary { color: var(--text) !important; font-size: 13px; }
.stTextArea textarea { background: var(--s2) !important; color: var(--text) !important; border: 1px solid var(--border) !important; font-family: var(--mono) !important; font-size: 12px !important; border-radius: var(--r) !important; }
</style>
""", unsafe_allow_html=True)


# ── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_checklist():
    p = Path("checklist.json")
    return json.loads(p.read_text()) if p.exists() else []

@st.cache_data
def load_verdicts():
    p = Path("verdicts.json")
    if p.exists():
        return json.loads(p.read_text())
    import hashlib
    checklist = load_checklist()
    mock = {}
    for i, rule in enumerate(checklist):
        rid = rule.get("chapter_step_id") or rule.get("step_id") or f"rule-{i}"
        h = int(hashlib.md5(str(rid).encode()).hexdigest(), 16) % 100
        if h < 70:
            verdict, note = "Compliant", "Operator action observed; acceptance criterion met."
        elif h < 90:
            verdict, note = "Deviation Detected", "Component used does not match SOP requirement."
        else:
            verdict, note = "Unable to Verify", "Action occurred outside camera view."
        mock[str(rid)] = {"verdict": verdict, "confidence": 0.62 + (h % 35) / 100,
                          "evidence_timestamp": f"00:{(i % 9)+1:02d}:{(i*7)%60:02d}",
                          "note": note, "_mock": True}
    return mock

@st.cache_data
def load_sop_text():
    if not AZURE_OK:
        return None
    try:
        c = SearchClient(os.environ["SEARCH_ENDPOINT"], os.environ["SEARCH_INDEX_NAME"],
                         AzureKeyCredential(os.environ["SEARCH_ADMIN_KEY"]))
        for r in c.search(search_text="*", select=["content"], top=1):
            return r["content"]
    except Exception:
        return None

def adherence(verdicts):
    if not verdicts:
        return {"score": 0, "compliant": 0, "deviation": 0, "unable": 0, "total": 0}
    counts = defaultdict(int)
    for v in verdicts.values():
        counts[v.get("verdict", "Unable to Verify")] += 1
    total = sum(counts.values())
    score = round(100 * counts["Compliant"] / total) if total else 0
    return {"score": score, "compliant": counts["Compliant"],
            "deviation": counts["Deviation Detected"], "unable": counts["Unable to Verify"],
            "total": total}

def chapter_stats(checklist, verdicts):
    by_ch = defaultdict(lambda: {"pass": 0, "fail": 0, "warn": 0, "total": 0})
    for rule in checklist:
        rid = str(rule.get("chapter_step_id") or rule.get("step_id") or "?")
        ch = rid.split(".")[0] if "." in rid else "?"
        v = verdicts.get(rid, {})
        verdict = v.get("verdict", "Pending")
        by_ch[ch]["total"] += 1
        if verdict == "Compliant":              by_ch[ch]["pass"] += 1
        elif verdict == "Deviation Detected":   by_ch[ch]["fail"] += 1
        else:                                   by_ch[ch]["warn"] += 1
    return by_ch


# ── Charts ────────────────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, Arial", color="#6E6151"),
    margin=dict(l=0, r=0, t=0, b=0),
)

def make_donut(s):
    labels = ["Compliant", "Deviation", "Unable to Verify"]
    values = [s["compliant"], s["deviation"], s["unable"]]
    colors = ["#7A8C52", "#C8694B", "#E8DEC9"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.72,
        marker=dict(colors=colors, line=dict(color="#FBF7EE", width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} steps (%{percent})<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{s['score']}%</b>",
        x=0.5, y=0.55, showarrow=False,
        font=dict(size=36, color="#3D3528", family="DM Sans"),
        xanchor="center",
    )
    fig.add_annotation(
        text="adherence",
        x=0.5, y=0.38, showarrow=False,
        font=dict(size=11, color="#A0917A", family="JetBrains Mono"),
        xanchor="center",
    )
    fig.update_layout(**PLOTLY_BASE, height=260, showlegend=False)
    return fig

def make_chapter_bars(checklist, verdicts):
    stats = chapter_stats(checklist, verdicts)
    chapters = sorted(stats.keys(), key=lambda x: int(x) if x.isdigit() else 99)
    labels = [f"Ch {ch}" for ch in chapters]
    pct_pass = [round(100 * stats[ch]["pass"] / stats[ch]["total"]) if stats[ch]["total"] else 0 for ch in chapters]
    pct_fail = [round(100 * stats[ch]["fail"] / stats[ch]["total"]) if stats[ch]["total"] else 0 for ch in chapters]
    pct_warn = [round(100 * stats[ch]["warn"] / stats[ch]["total"]) if stats[ch]["total"] else 0 for ch in chapters]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Compliant",    y=labels, x=pct_pass, orientation="h",
                         marker_color="#7A8C52", marker_opacity=0.8,
                         hovertemplate="%{y}: %{x}% compliant<extra></extra>"))
    fig.add_trace(go.Bar(name="Deviation",    y=labels, x=pct_fail, orientation="h",
                         marker_color="#C8694B", marker_opacity=0.8,
                         hovertemplate="%{y}: %{x}% deviation<extra></extra>"))
    fig.add_trace(go.Bar(name="Unable",       y=labels, x=pct_warn, orientation="h",
                         marker_color="#C2913C", marker_opacity=0.65,
                         hovertemplate="%{y}: %{x}% unverified<extra></extra>"))
    fig.update_layout(
        **PLOTLY_BASE, barmode="stack", height=max(200, len(chapters) * 30 + 40),
        xaxis=dict(range=[0, 100], ticksuffix="%", tickfont=dict(size=10, family="JetBrains Mono"),
                   gridcolor="#E2D6BF", gridwidth=1, zeroline=False),
        yaxis=dict(tickfont=dict(size=10, family="JetBrains Mono"), gridcolor="#E2D6BF"),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0, font=dict(size=10, family="JetBrains Mono"),
                    bgcolor="rgba(0,0,0,0)", itemsizing="constant"),
        bargap=0.35,
    )
    return fig

def make_scatter_timeline(verdicts):
    points = [(rid, v) for rid, v in verdicts.items() if v.get("evidence_timestamp")]

    def ts_to_sec(ts):
        try:
            parts = ts.split(":")
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            return 0

    def verdict_style(v):
        verdict = v.get("verdict", "Pending")
        return {
            "Compliant":           ("#7A8C52", 8, "circle"),
            "Deviation Detected":  ("#C8694B", 12, "diamond"),
            "Unable to Verify":    ("#C2913C", 9, "triangle-up"),
        }.get(verdict, ("#A0917A", 7, "circle"))

    if not points:
        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE, height=160)
        return fig

    by_verdict = defaultdict(list)
    for rid, v in points:
        by_verdict[v.get("verdict", "Pending")].append((rid, v))

    fig = go.Figure()
    cfg = {
        "Compliant":          ("#7A8C52", 8,  "circle",      "Compliant"),
        "Deviation Detected": ("#C8694B", 13, "diamond",     "Deviation"),
        "Unable to Verify":   ("#C2913C", 9,  "triangle-up", "Unable to Verify"),
    }
    for verdict, (color, size, symbol, name) in cfg.items():
        pts = by_verdict.get(verdict, [])
        if not pts:
            continue
        x = [ts_to_sec(v["evidence_timestamp"]) for _, v in pts]
        y = [round(v.get("confidence", 0) * 100) for _, v in pts]
        rid_labels = [rid for rid, _ in pts]
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers", name=name,
            marker=dict(color=color, size=size, symbol=symbol,
                        line=dict(color="#FBF7EE", width=1.5)),
            hovertemplate=(
                f"<b>{name}</b><br>"
                "Step: %{customdata}<br>"
                "Confidence: %{y}%<br>"
                "Time: %{x}s<extra></extra>"
            ),
            customdata=rid_labels,
        ))

    fig.update_layout(
        **PLOTLY_BASE, height=200,
        xaxis=dict(title=dict(text="seconds", font=dict(size=9, family="JetBrains Mono")),
                   tickfont=dict(size=9, family="JetBrains Mono"),
                   gridcolor="#E2D6BF", zeroline=False),
        yaxis=dict(title=dict(text="confidence %", font=dict(size=9, family="JetBrains Mono")),
                   tickfont=dict(size=9, family="JetBrains Mono"),
                   gridcolor="#E2D6BF", range=[0, 105], zeroline=False),
        showlegend=True,
        legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10, family="JetBrains Mono"),
                    bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────
checklist = load_checklist()
verdicts  = load_verdicts()
sop_text  = load_sop_text()
mock_active = any(v.get("_mock") for v in verdicts.values())
s = adherence(verdicts)

st.sidebar.markdown(f"""
<div class="pg-brand">
  <div class="pg-mark">
    <svg viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9 1.5L2.25 4.5V9C2.25 12.728 5.178 16.2 9 17.25C12.822 16.2 15.75 12.728 15.75 9V4.5L9 1.5Z"
            stroke="white" stroke-width="1.25" stroke-linejoin="round"/>
      <path d="M6 9L8 11L12 7" stroke="white" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div>
    <div class="pg-name">ProcedureGuard</div>
    <div class="pg-tag">Compliance AI</div>
  </div>
</div>
<div class="pg-nav-section">Pages</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("", [
    "Compliance Summary",
    "Checklist Viewer",
    "SOP Reference",
    "Q&A Chat",
], label_visibility="collapsed")

st.sidebar.markdown(f"""
<div class="pg-sb-div"></div>
<div class="pg-sb-block">
  <div class="pg-sb-hdr">Pipeline</div>
  <div class="pg-sb-row"><span class="pg-sb-k">Rules</span><span class="pg-sb-v">{len(checklist)}</span></div>
  <div class="pg-sb-row"><span class="pg-sb-k">Verdicts</span><span class="pg-sb-v">{len(verdicts)}</span></div>
  <div class="pg-sb-row"><span class="pg-sb-k">Score</span><span class="pg-sb-v">{s['score']}%</span></div>
  <div class="pg-sb-row"><span class="pg-sb-k">SOP</span><span class="pg-sb-v">{'AI Search' if sop_text else 'offline'}</span></div>
  <div class="pg-sb-row"><span class="pg-sb-k">GPT-4o</span><span class="pg-sb-v">{'ready' if os.environ.get('GITHUB_TOKEN') else 'no token'}</span></div>
</div>
""", unsafe_allow_html=True)

if mock_active:
    st.sidebar.warning("Mock data active — re-run Agent 2 once quota resets.")


# ── Run top bar (all pages) ───────────────────────────────────────────────────
mode_cls   = "pg-mode-mock" if mock_active else "pg-mode-live"
mode_label = "MOCK" if mock_active else "LIVE"
st.markdown(f"""
<div class="pg-topbar">
  <div>
    <div class="pg-topbar-title">STEMFIE Vehicle Assembly</div>
    <div class="pg-topbar-sub">Procedure A · build → state 13</div>
  </div>
  <div class="pg-topbar-divider"></div>
  <div class="pg-topbar-meta">
    <span class="pg-topbar-mk">Run ID</span>
    <span class="pg-topbar-mv">RUN-2026-06-15-001</span>
  </div>
  <div class="pg-topbar-divider"></div>
  <div class="pg-topbar-meta">
    <span class="pg-topbar-mk">Inspector</span>
    <span class="pg-topbar-mv">Agent 2 · GPT-4o Vision</span>
  </div>
  <div class="pg-topbar-divider"></div>
  <div class="pg-topbar-meta">
    <span class="pg-topbar-mk">Threshold</span>
    <span class="pg-topbar-mv">95% · Chapter 8 rework</span>
  </div>
  <div class="{mode_cls}">
    <div class="pg-mode-dot"></div>
    <span class="pg-mode-label">{mode_label}</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — COMPLIANCE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
if page == "Compliance Summary":
    score = s["score"]

    if score >= 85:
        bar_color, vk = "#7A8C52", "pass"
        v_title = "PASS — Vehicle cleared for release"
        v_msg   = "All compliance checks passed within acceptable thresholds."
    elif s["deviation"] > 0:
        bar_color, vk = "#C8694B", "fail"
        v_title = f"FAIL — {s['deviation']} deviation(s) detected"
        v_msg   = "Quarantine the unit and follow Chapter 8 rework procedure."
    else:
        bar_color, vk = "#C2913C", "hold"
        v_title = "HOLD — Manual review required"
        v_msg   = f"{s['unable']} step(s) could not be verified from footage."

    # ── Hero ─────────────────────────────────────────────────────────────────
    col_hero, col_donut = st.columns([1.1, 0.9])

    with col_hero:
        st.markdown(f"""
        <div class="pg-hero-wrap">
          <div class="pg-score-sweep"></div>
          <div class="pg-score-eyebrow">Adherence Score</div>
          <div class="pg-score-number">
            {score}<span class="pg-score-pct">%</span>
          </div>
          <div class="pg-score-bar-wrap">
            <div class="pg-score-bar-track">
              <div class="pg-score-bar-fill" style="width:{score}%;background:{bar_color};"></div>
            </div>
            <div class="pg-score-threshold">
              <div class="pg-score-thr-line">
                Release threshold: <span class="pg-score-thr-val">95%</span>
              </div>
            </div>
          </div>
          <div class="pg-verdict {vk}">
            <div class="pg-v-dot"></div>
            <div>
              <div class="pg-v-title">{v_title}</div>
              <div class="pg-v-msg">{v_msg}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_donut:
        st.markdown('<div class="pg-panel" style="height:100%"><div class="pg-panel-title">Breakdown</div>', unsafe_allow_html=True)
        st.plotly_chart(make_donut(s), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Metric strip ─────────────────────────────────────────────────────────
    total = s["total"] or 1
    metrics = [
        ("pass", "Compliant", s["compliant"], round(s["compliant"] / total * 100)),
        ("fail", "Deviations", s["deviation"], round(s["deviation"] / total * 100)),
        ("warn", "Unable to Verify", s["unable"], round(s["unable"] / total * 100)),
        ("info", "Total Inspected", s["total"], 100),
    ]
    cols = st.columns(4)
    for col, (cls, label, val, pct) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="pg-metric {cls}">
              <div class="pg-metric-label">{label}</div>
              <div class="pg-metric-val">{val}</div>
              <div class="pg-metric-bar-track">
                <div class="pg-metric-bar-fill" style="width:{pct}%"></div>
              </div>
              <div class="pg-metric-sub">{pct}% of total</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Chapter bars + Compliance matrix ─────────────────────────────────────
    st.markdown("""
    <div class="pg-section">
      <span class="pg-section-label">Chapter Breakdown</span>
    </div>""", unsafe_allow_html=True)

    col_bars, col_matrix = st.columns([1.1, 0.9])

    with col_bars:
        st.markdown('<div class="pg-panel"><div class="pg-panel-title">Compliance by Chapter</div>', unsafe_allow_html=True)
        if checklist:
            st.plotly_chart(make_chapter_bars(checklist, verdicts), use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.markdown('<div style="color:var(--dim);font-size:13px;padding:24px 0;text-align:center;">No checklist loaded.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_matrix:
        st.markdown('<div class="pg-panel"><div class="pg-panel-title">Step Matrix</div>', unsafe_allow_html=True)
        if checklist:
            cells_html = ""
            for rule in checklist:
                rid = str(rule.get("chapter_step_id") or rule.get("step_id") or "?")
                v   = verdicts.get(rid, {})
                verdict = v.get("verdict", "Pending")
                cell_cls = {
                    "Compliant": "pg-cell-pass",
                    "Deviation Detected": "pg-cell-fail",
                    "Unable to Verify": "pg-cell-warn",
                }.get(verdict, "pg-cell-hold")
                action_short = (rule.get("action") or "")[:60]
                cells_html += f'<div class="pg-cell {cell_cls}" title="{rid}: {action_short}"></div>'
            st.markdown(f"""
            <div class="pg-matrix">{cells_html}</div>
            <div class="pg-matrix-legend">
              <div class="pg-legend-item"><div class="pg-legend-dot" style="background:#7A8C52"></div><span class="pg-legend-label">Compliant</span></div>
              <div class="pg-legend-item"><div class="pg-legend-dot" style="background:#C8694B"></div><span class="pg-legend-label">Deviation</span></div>
              <div class="pg-legend-item"><div class="pg-legend-dot" style="background:#C2913C"></div><span class="pg-legend-label">Unable</span></div>
              <div class="pg-legend-item"><div class="pg-legend-dot" style="background:#E8DEC9;border:1px solid #E2D6BF"></div><span class="pg-legend-label">Pending</span></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--dim);font-size:13px;padding:24px 0;text-align:center;">No checklist loaded.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Scatter timeline ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="pg-section">
      <span class="pg-section-label">Event Timeline</span>
      <span class="pg-section-badge">all verdicts by confidence</span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="pg-panel"><div class="pg-panel-title">Confidence vs. Time</div>', unsafe_allow_html=True)
    st.plotly_chart(make_scatter_timeline(verdicts), use_container_width=True,
                    config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Deviation cards ───────────────────────────────────────────────────────
    deviations = sorted(
        [(rid, v) for rid, v in verdicts.items() if v.get("verdict") == "Deviation Detected"],
        key=lambda kv: kv[1].get("evidence_timestamp", "")
    )
    st.markdown(f"""
    <div class="pg-section">
      <span class="pg-section-label">Deviation Log</span>
      <span class="pg-section-badge">{len(deviations)} events</span>
    </div>""", unsafe_allow_html=True)

    if not deviations:
        st.markdown('<div style="background:var(--s1);border:1px solid var(--border);border-radius:8px;padding:32px;text-align:center;color:var(--dim);">No deviations detected in this run.</div>', unsafe_allow_html=True)
    else:
        for rid, v in deviations:
            rule = next((r for r in checklist if str(r.get("chapter_step_id") or r.get("step_id")) == rid), {})
            action_text = (rule.get("action") or "Unknown step")[:100]
            conf_pct = round(v.get("confidence", 0) * 100)
            st.markdown(f"""
            <div class="pg-dev">
              <div class="pg-dev-ts">
                <div class="pg-dev-ts-dot"></div>
                {v.get('evidence_timestamp', '?')}
              </div>
              <div>
                <div class="pg-dev-step">Step {rid}</div>
                <div class="pg-dev-action">{action_text}</div>
              </div>
              <div class="pg-dev-conf">CONF {conf_pct}%</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("Evidence + SOP reference"):
                st.write(f"**Reason:** {v.get('note', '—')}")
                if rule.get("acceptance_criterion"):
                    st.write(f"**Criterion:** {rule['acceptance_criterion']}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — CHECKLIST VIEWER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Checklist Viewer":
    if not checklist:
        st.warning("No checklist found.")
    else:
        by_chapter = defaultdict(list)
        for r in checklist:
            csid = str(r.get("chapter_step_id", r.get("step_id", "?")))
            ch = csid.split(".")[0] if "." in csid else "Other"
            by_chapter[ch].append(r)

        for ch in sorted(by_chapter.keys(), key=lambda x: int(x) if x.isdigit() else 99):
            rules = by_chapter[ch]
            ch_pass = sum(1 for r in rules if verdicts.get(str(r.get("chapter_step_id") or r.get("step_id")), {}).get("verdict") == "Compliant")
            st.markdown(f'<div class="pg-chapter-hdr">Chapter {ch} — {ch_pass}/{len(rules)} compliant</div>', unsafe_allow_html=True)
            for rule in rules:
                rid = rule.get("chapter_step_id") or rule.get("step_id") or "?"
                v = verdicts.get(str(rid), {})
                verdict = v.get("verdict", "Pending")
                cls, badge = {
                    "Compliant":          ("pass", "pass"),
                    "Deviation Detected": ("fail", "fail"),
                    "Unable to Verify":   ("warn", "warn"),
                }.get(verdict, ("hold", "hold"))
                ts_part = f" · {v['evidence_timestamp']}" if v.get("evidence_timestamp") else ""
                st.markdown(f"""
                <div class="pg-rule {cls}">
                  <div class="pg-rule-hdr">
                    <span class="pg-rule-id">{rid}{ts_part}</span>
                    <span class="pg-rule-badge {badge}">{verdict}</span>
                  </div>
                  <div class="pg-rule-action">{(rule.get('action') or '—')[:220]}</div>
                </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SOP REFERENCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "SOP Reference":
    if sop_text:
        st.text_area("SOP", value=sop_text, height=700, label_visibility="collapsed")
    else:
        st.warning("SOP source unavailable. Load .env: `set -a && source .env && set +a`")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Q&A CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Q&A Chat":
    if not OPENAI_OK:
        st.error("openai package not installed.")
    elif not os.environ.get("GITHUB_TOKEN"):
        st.warning("GITHUB_TOKEN not in environment.")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "system", "content": "You are a compliance assistant. Answer questions about the SOP factually."}
            ]
            if sop_text:
                st.session_state.messages.append({"role": "system", "content": f"SOP:\n{sop_text[:6000]}"})

        for msg in st.session_state.messages:
            if msg["role"] == "system": continue
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        prompt = st.chat_input("Ask about the SOP...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                placeholder = st.empty()
                try:
                    client = OpenAI(
                        api_key=os.environ["GITHUB_TOKEN"],
                        base_url=os.environ.get("GPT4O_BASE_URL", "https://models.inference.ai.azure.com"),
                    )
                    resp = client.chat.completions.create(
                        model="gpt-4o", messages=st.session_state.messages, temperature=0.2,
                    )
                    reply = resp.choices[0].message.content
                    placeholder.write(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RateLimit" in err:
                        placeholder.error("GitHub Models quota exhausted. Resets at 5:30 AM IST.")
                    else:
                        placeholder.error(f"Error: {err[:200]}")
