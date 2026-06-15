"""ProcedureGuard Dashboard v3 - Hero layout with adherence gauge."""
import json
import os
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

st.markdown("""
<style>
  :root {
    --pg-bg: #0A1020; --pg-surface: #141C30; --pg-surface-2: #1C2540;
    --pg-border: #2A3658; --pg-text: #ECF0F8; --pg-text-dim: #8B95B0;
    --pg-accent: #4A90E2; --pg-pass: #22D89A; --pg-fail: #FF5757;
    --pg-warn: #FFB547; --pg-hold: #8B95B0;
  }
  .stApp { background: var(--pg-bg); }
  section[data-testid="stSidebar"] { background: var(--pg-surface) !important; border-right: 1px solid var(--pg-border); }
  section[data-testid="stSidebar"] * { color: var(--pg-text) !important; }
  h1, h2, h3 { color: var(--pg-text) !important; letter-spacing: -0.02em; }
  div[data-testid="stMarkdownContainer"] p { color: var(--pg-text-dim); }
  #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
  .block-container { padding-top: 1rem !important; max-width: 1500px !important; }
  .pg-brand { display: flex; align-items: center; gap: 12px; padding: 0 0 16px 0; border-bottom: 1px solid var(--pg-border); margin-bottom: 16px; }
  .pg-brand-icon { width: 38px; height: 38px; background: linear-gradient(135deg, #4A90E2, #6FB1FC); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
  .pg-brand-name { font-size: 17px; font-weight: 700; color: var(--pg-text); margin: 0; line-height: 1.2; }
  .pg-brand-tag { font-size: 10px; color: var(--pg-text-dim); margin: 0; text-transform: uppercase; letter-spacing: 1.5px; }
  .pg-runbar { background: linear-gradient(90deg, var(--pg-surface) 0%, var(--pg-surface-2) 100%); border: 1px solid var(--pg-border); border-radius: 12px; padding: 14px 24px; margin-bottom: 18px; display: grid; grid-template-columns: 1fr auto auto auto; gap: 28px; align-items: center; }
  .pg-runbar-title { font-size: 18px; font-weight: 700; color: var(--pg-text); margin: 0; }
  .pg-runbar-sub { font-size: 12px; color: var(--pg-text-dim); margin: 2px 0 0 0; }
  .pg-runbar-meta { display: flex; flex-direction: column; gap: 2px; }
  .pg-runbar-mk { font-size: 10px; color: var(--pg-text-dim); text-transform: uppercase; letter-spacing: 1.5px; }
  .pg-runbar-mv { font-size: 13px; color: var(--pg-text); font-weight: 600; font-family: 'SF Mono', Monaco, monospace; }
  .pg-hero { background: var(--pg-surface); border: 1px solid var(--pg-border); border-radius: 14px; padding: 28px; margin-bottom: 18px; }
  .pg-verdict { border-radius: 10px; padding: 16px 22px; margin: 18px 0 0 0; border-left: 5px solid; display: flex; align-items: center; gap: 14px; }
  .pg-verdict.pass { background: rgba(34,216,154,0.08); border-left-color: var(--pg-pass); }
  .pg-verdict.fail { background: rgba(255,87,87,0.08);  border-left-color: var(--pg-fail); }
  .pg-verdict.hold { background: rgba(255,181,71,0.08); border-left-color: var(--pg-warn); }
  .pg-verdict-icon { font-size: 24px; }
  .pg-verdict-title { font-size: 14px; font-weight: 700; color: var(--pg-text); margin: 0; text-transform: uppercase; letter-spacing: 1.5px; }
  .pg-verdict-msg { font-size: 13px; color: var(--pg-text-dim); margin: 3px 0 0 0; }
  .pg-stat { background: var(--pg-surface-2); border: 1px solid var(--pg-border); border-radius: 10px; padding: 16px 18px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 4px; border-left: 3px solid; }
  .pg-stat.pass { border-left-color: var(--pg-pass); }
  .pg-stat.fail { border-left-color: var(--pg-fail); }
  .pg-stat.warn { border-left-color: var(--pg-warn); }
  .pg-stat.info { border-left-color: var(--pg-accent); }
  .pg-stat-label { font-size: 10px; color: var(--pg-text-dim); font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; margin: 0; }
  .pg-stat-row { display: flex; justify-content: space-between; align-items: baseline; margin: 2px 0 0 0; }
  .pg-stat-val { font-size: 26px; font-weight: 700; color: var(--pg-text); margin: 0; line-height: 1.1; }
  .pg-stat-pct { font-size: 12px; color: var(--pg-text-dim); font-weight: 500; }
  .pg-section { display: flex; align-items: center; justify-content: space-between; margin: 22px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid var(--pg-border); }
  .pg-section h3 { margin: 0; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; color: var(--pg-text); }
  .pg-section-count { font-size: 11px; color: var(--pg-text-dim); background: var(--pg-surface); padding: 4px 10px; border-radius: 12px; border: 1px solid var(--pg-border); font-family: 'SF Mono', Monaco, monospace; }
  .pg-dev { background: var(--pg-surface); border: 1px solid var(--pg-border); border-left: 3px solid var(--pg-fail); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; display: grid; grid-template-columns: auto 90px 1fr auto; gap: 14px; align-items: center; }
  .pg-dev-icon { font-size: 16px; }
  .pg-dev-time { font-family: 'SF Mono', Monaco, monospace; color: var(--pg-warn); font-size: 12px; font-weight: 600; }
  .pg-dev-step { color: var(--pg-text); font-weight: 600; font-size: 13px; margin: 0; }
  .pg-dev-action { color: var(--pg-text-dim); font-size: 12px; margin: 1px 0 0 0; }
  .pg-dev-conf { font-family: 'SF Mono', Monaco, monospace; font-size: 11px; color: var(--pg-text-dim); background: var(--pg-surface-2); padding: 4px 10px; border-radius: 4px; border: 1px solid var(--pg-border); }
  .pg-sb-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--pg-border); }
  .pg-sb-row:last-child { border-bottom: none; }
  .pg-sb-label { font-size: 11px; color: var(--pg-text-dim); }
  .pg-sb-val { font-size: 11px; color: var(--pg-text); font-weight: 600; font-family: 'SF Mono', Monaco, monospace; }
  .pg-rule { background: var(--pg-surface); border: 1px solid var(--pg-border); border-left: 3px solid; border-radius: 6px; padding: 11px 15px; margin-bottom: 7px; }
  .pg-rule.pass { border-left-color: var(--pg-pass); }
  .pg-rule.fail { border-left-color: var(--pg-fail); }
  .pg-rule.warn { border-left-color: var(--pg-warn); }
  .pg-rule.hold { border-left-color: var(--pg-hold); }
  .pg-rule-header { display: flex; justify-content: space-between; align-items: center; }
  .pg-rule-id { font-family: 'SF Mono', Monaco, monospace; font-size: 11px; color: var(--pg-accent); font-weight: 600; }
  .pg-rule-badge { font-size: 9px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .pg-rule-badge.pass { background: rgba(34,216,154,0.15); color: var(--pg-pass); }
  .pg-rule-badge.fail { background: rgba(255,87,87,0.15); color: var(--pg-fail); }
  .pg-rule-badge.warn { background: rgba(255,181,71,0.15); color: var(--pg-warn); }
  .pg-rule-badge.hold { background: rgba(139,149,176,0.15); color: var(--pg-hold); }
  .pg-rule-action { color: var(--pg-text); font-size: 13px; margin: 5px 0 0 0; }
  .pg-chapter-header { font-size: 12px; font-weight: 700; color: var(--pg-accent); text-transform: uppercase; letter-spacing: 2px; margin: 20px 0 8px 0; padding-bottom: 6px; border-bottom: 1px solid var(--pg-border); }
  .stRadio > div { gap: 0 !important; }
  .stRadio label { padding: 10px 14px !important; border-radius: 6px !important; margin: 2px 0 !important; cursor: pointer; }
  .stRadio label:hover { background: var(--pg-surface-2) !important; }
  .stRadio [data-baseweb="radio"] { display: none !important; }
  .stChatMessage { background: var(--pg-surface) !important; border: 1px solid var(--pg-border) !important; }
  details { background: var(--pg-surface); border: 1px solid var(--pg-border); border-radius: 6px; padding: 8px 14px; margin-bottom: 6px; }
  details summary { color: var(--pg-text) !important; }
  .stTextArea textarea { background: var(--pg-surface) !important; color: var(--pg-text) !important; border: 1px solid var(--pg-border) !important; font-family: 'SF Mono', Monaco, monospace !important; font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)


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
        mock[str(rid)] = {"verdict": verdict, "confidence": 0.65 + (h % 30) / 100,
                          "evidence_timestamp": f"00:{(i % 9) + 1:02d}:{(i * 7) % 60:02d}",
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
    return None


def adherence(verdicts):
    if not verdicts:
        return {"score": 0, "compliant": 0, "deviation": 0, "unable": 0, "total": 0}
    counts = {"Compliant": 0, "Deviation Detected": 0, "Unable to Verify": 0}
    for v in verdicts.values():
        counts[v.get("verdict", "Unable to Verify")] = counts.get(v.get("verdict"), 0) + 1
    total = sum(counts.values())
    score = round(100 * counts["Compliant"] / total) if total else 0
    return {"score": score, "compliant": counts["Compliant"],
            "deviation": counts["Deviation Detected"], "unable": counts["Unable to Verify"],
            "total": total}


def make_gauge(score, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"suffix": "%", "font": {"size": 56, "color": "#ECF0F8", "family": "Arial"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickfont": {"size": 11, "color": "#8B95B0"}},
            "bar": {"color": color, "thickness": 0.65},
            "bgcolor": "#1C2540", "borderwidth": 0,
            "steps": [
                {"range": [0, 60], "color": "rgba(255,87,87,0.10)"},
                {"range": [60, 85], "color": "rgba(255,181,71,0.10)"},
                {"range": [85, 100], "color": "rgba(34,216,154,0.10)"},
            ],
            "threshold": {"line": {"color": "#4A90E2", "width": 2}, "thickness": 0.75, "value": 95},
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=20, r=20, t=20, b=20), height=300,
                      font={"color": "#ECF0F8", "family": "Arial"})
    return fig


st.sidebar.markdown("""
<div class="pg-brand">
  <div class="pg-brand-icon">🛡️</div>
  <div>
    <p class="pg-brand-name">ProcedureGuard</p>
    <p class="pg-brand-tag">Compliance Verification</p>
  </div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigation",
    ["📊 Compliance Summary", "📋 Checklist Viewer", "📄 SOP Reference", "💬 Q&A Chat"],
    label_visibility="collapsed")

st.sidebar.markdown("---")
checklist = load_checklist()
verdicts = load_verdicts()
sop_text = load_sop_text()
mock_active = any(v.get("_mock") for v in verdicts.values())

st.sidebar.markdown('<p style="font-size:10px;font-weight:600;color:#8B95B0;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px 0;">Pipeline Status</p>', unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div class="pg-sb-row"><span class="pg-sb-label">Checklist rules</span><span class="pg-sb-val">{len(checklist)}</span></div>
<div class="pg-sb-row"><span class="pg-sb-label">Verdicts</span><span class="pg-sb-val">{len(verdicts)}{' mock' if mock_active else ''}</span></div>
<div class="pg-sb-row"><span class="pg-sb-label">SOP source</span><span class="pg-sb-val">{'AI Search' if sop_text else 'offline'}</span></div>
<div class="pg-sb-row"><span class="pg-sb-label">GPT-4o</span><span class="pg-sb-val">{'ready' if os.environ.get('GITHUB_TOKEN') else 'no token'}</span></div>
""", unsafe_allow_html=True)

if mock_active:
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.warning("Using mock verdicts. Re-run Agent 2 once quota resets.", icon="⚠️")


if page.endswith("Compliance Summary"):
    s = adherence(verdicts)
    score = s["score"]
    if score >= 85:
        gauge_color, verdict_kind = "#22D89A", "pass"
        verdict_title = "PASS — Vehicle cleared for release"
        verdict_msg = "All compliance checks passed within acceptable thresholds."
    elif s["deviation"] > 0:
        gauge_color, verdict_kind = "#FF5757", "fail"
        verdict_title = f"FAIL — {s['deviation']} deviation(s) detected"
        verdict_msg = "Quarantine the unit and follow Chapter 8 rework procedure."
    else:
        gauge_color, verdict_kind = "#FFB547", "hold"
        verdict_title = "HOLD — Manual review required"
        verdict_msg = f"{s['unable']} step(s) could not be verified."

    st.markdown(f"""
    <div class="pg-runbar">
      <div>
        <p class="pg-runbar-title">Compliance Summary</p>
        <p class="pg-runbar-sub">STEMFIE Vehicle Assembly · Procedure A · Run inspection report</p>
      </div>
      <div class="pg-runbar-meta"><span class="pg-runbar-mk">Run ID</span><span class="pg-runbar-mv">RUN-2026-06-15-001</span></div>
      <div class="pg-runbar-meta"><span class="pg-runbar-mk">Procedure</span><span class="pg-runbar-mv">A · build → state 13</span></div>
      <div class="pg-runbar-meta"><span class="pg-runbar-mk">Mode</span><span class="pg-runbar-mv">{'MOCK' if mock_active else 'LIVE'}</span></div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.markdown('<div class="pg-hero">', unsafe_allow_html=True)
        st.plotly_chart(make_gauge(score, gauge_color), use_container_width=True, config={"displayModeBar": False})
        icon = {'pass':'✅','fail':'⛔','hold':'⚠️'}[verdict_kind]
        st.markdown(f"""
        <div style="text-align: center; margin-top: -20px;">
          <p style="font-size:10px;color:#8B95B0;font-weight:700;text-transform:uppercase;letter-spacing:2.5px;margin:0;">Adherence Score</p>
          <p style="font-size:11px;color:#8B95B0;margin:4px 0 0 0;">Threshold for release: <b style="color:#4A90E2;">95%</b></p>
        </div>
        <div class="pg-verdict {verdict_kind}">
          <div class="pg-verdict-icon">{icon}</div>
          <div>
            <p class="pg-verdict-title">{verdict_title}</p>
            <p class="pg-verdict-msg">{verdict_msg}</p>
          </div>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        total = s["total"] or 1
        pct_pass = s["compliant"] / total * 100
        pct_dev = s["deviation"] / total * 100
        pct_un = s["unable"] / total * 100
        st.markdown(f"""
        <div class="pg-stat pass"><p class="pg-stat-label">● Compliant</p><div class="pg-stat-row"><p class="pg-stat-val">{s['compliant']}</p><p class="pg-stat-pct">{pct_pass:.1f}% of total</p></div></div>
        <div class="pg-stat fail"><p class="pg-stat-label">● Deviations</p><div class="pg-stat-row"><p class="pg-stat-val">{s['deviation']}</p><p class="pg-stat-pct">{pct_dev:.1f}% of total</p></div></div>
        <div class="pg-stat warn"><p class="pg-stat-label">● Unable to Verify</p><div class="pg-stat-row"><p class="pg-stat-val">{s['unable']}</p><p class="pg-stat-pct">{pct_un:.1f}% of total</p></div></div>
        <div class="pg-stat info"><p class="pg-stat-label">● Total Steps Inspected</p><div class="pg-stat-row"><p class="pg-stat-val">{s['total']}</p><p class="pg-stat-pct">by Agent 2 inspector</p></div></div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="pg-section">
      <h3>Deviation Timeline</h3>
      <span class="pg-section-count">{s['deviation']} EVENTS</span>
    </div>
    """, unsafe_allow_html=True)

    deviations = [(rid, v) for rid, v in verdicts.items() if v.get("verdict") == "Deviation Detected"]
    deviations.sort(key=lambda kv: kv[1].get("evidence_timestamp", ""))
    if not deviations:
        st.markdown('<div style="background:var(--pg-surface);border:1px solid var(--pg-border);border-radius:8px;padding:24px;text-align:center;color:var(--pg-text-dim);">No deviations detected.</div>', unsafe_allow_html=True)
    else:
        for rid, v in deviations:
            rule = next((r for r in checklist if str(r.get("chapter_step_id") or r.get("step_id")) == rid), {})
            action_text = (rule.get("action") or "Unknown step")[:90]
            conf_pct = int(v.get("confidence", 0) * 100)
            st.markdown(f"""
            <div class="pg-dev">
              <div class="pg-dev-icon">⚠️</div>
              <div class="pg-dev-time">{v.get('evidence_timestamp', '?')}</div>
              <div><p class="pg-dev-step">Step {rid}</p><p class="pg-dev-action">{action_text}</p></div>
              <div class="pg-dev-conf">CONF {conf_pct}%</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("Evidence and SOP reference"):
                st.write(f"**Reason:** {v.get('note', '—')}")
                if rule.get("acceptance_criterion"):
                    st.write(f"**Acceptance criterion:** {rule['acceptance_criterion']}")


elif page.endswith("Checklist Viewer"):
    st.markdown(f"""
    <div class="pg-runbar">
      <div><p class="pg-runbar-title">Compliance Checklist</p><p class="pg-runbar-sub">{len(checklist)} rules generated by Agent 1</p></div>
    </div>
    """, unsafe_allow_html=True)
    if not checklist:
        st.warning("No checklist found.")
    else:
        by_chapter = defaultdict(list)
        for r in checklist:
            csid = str(r.get("chapter_step_id", r.get("step_id", "?")))
            ch = csid.split(".")[0] if "." in csid else "Other"
            by_chapter[ch].append(r)
        for ch in sorted(by_chapter.keys(), key=lambda x: int(x) if x.isdigit() else 99):
            st.markdown(f'<div class="pg-chapter-header">Chapter {ch}</div>', unsafe_allow_html=True)
            for rule in by_chapter[ch]:
                rid = rule.get("chapter_step_id") or rule.get("step_id") or "?"
                v = verdicts.get(str(rid), {})
                verdict = v.get("verdict", "Pending")
                cls, badge = {"Compliant":("pass","pass"),"Deviation Detected":("fail","fail"),"Unable to Verify":("warn","warn")}.get(verdict, ("hold","hold"))
                ts_part = f' · {v["evidence_timestamp"]}' if v.get("evidence_timestamp") else ''
                st.markdown(f'<div class="pg-rule {cls}"><div class="pg-rule-header"><span class="pg-rule-id">{rid}{ts_part}</span><span class="pg-rule-badge {badge}">{verdict}</span></div><p class="pg-rule-action">{(rule.get("action") or "—")[:200]}</p></div>', unsafe_allow_html=True)


elif page.endswith("SOP Reference"):
    st.markdown('<div class="pg-runbar"><div><p class="pg-runbar-title">SOP Reference</p><p class="pg-runbar-sub">Source: Azure AI Search</p></div></div>', unsafe_allow_html=True)
    if sop_text:
        st.text_area("SOP", value=sop_text, height=700, label_visibility="collapsed")
    else:
        st.warning("SOP source unavailable. Load .env: set -a && source .env && set +a")


elif page.endswith("Q&A Chat"):
    st.markdown('<div class="pg-runbar"><div><p class="pg-runbar-title">Q&A Chat</p><p class="pg-runbar-sub">Ask GPT-4o about the SOP</p></div></div>', unsafe_allow_html=True)
    if not OPENAI_OK:
        st.error("openai package not installed.")
    elif not os.environ.get("GITHUB_TOKEN"):
        st.warning("GITHUB_TOKEN not in environment.")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role":"system","content":"You are a compliance assistant. Answer questions about the SOP factually."}]
            if sop_text:
                st.session_state.messages.append({"role":"system","content":f"SOP:\n{sop_text[:6000]}"})
        for msg in st.session_state.messages:
            if msg["role"] == "system": continue
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        prompt = st.chat_input("Ask about the SOP...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                placeholder = st.empty()
                try:
                    client = OpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url=os.environ.get("GPT4O_BASE_URL", "https://models.inference.ai.azure.com"))
                    resp = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages, temperature=0.2)
                    reply = resp.choices[0].message.content
                    placeholder.write(reply)
                    st.session_state.messages.append({"role":"assistant","content":reply})
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RateLimit" in err:
                        placeholder.error("GitHub Models quota exhausted. Resets at 5:30 AM IST.")
                    else:
                        placeholder.error(f"Error: {err[:200]}")
