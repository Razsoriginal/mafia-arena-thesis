"""Mafia Arena dashboard: streamlit run src/eval/dashboard.py
Tabs: Run Status | Costs | Games | Raw Logs | Docs | Config.
Secrets are never displayed (masked only). Live spend comes from
logs/*.parquet evidence + AiCredits wallet endpoint.
"""
import glob
import json
import os
import time
import urllib.request
import urllib.error

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _masked(key: str) -> str:
    v = os.getenv(key) or ""
    if len(v) > 12:
        return f"{v[:7]}...{v[-4:]} (len {len(v)})"
    return repr(v) if v else "(unset)"


@st.cache_data(ttl=15)
def load_progress() -> pd.DataFrame:
    p = os.path.join(ROOT, "logs", "progress.jsonl")
    if not os.path.exists(p):
        return pd.DataFrame()
    rows = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return pd.DataFrame(rows)


def list_outputs():
    files = []
    for pat in ("logs/*.parquet", "logs/raw/*.parquet"):
        for fp in glob.glob(os.path.join(ROOT, pat)):
            stt = os.stat(fp)
            files.append({"file": os.path.relpath(fp, ROOT),
                          "rows": _parquet_rows(fp),
                          "size_kb": round(stt.st_size / 1024, 1),
                          "modified": time.strftime("%H:%M:%S", time.localtime(stt.st_mtime))})
    return pd.DataFrame(files)


def _parquet_rows(fp: str):
    try:
        return len(pd.read_parquet(fp))
    except Exception:
        return "?"


@st.cache_data(ttl=60)
def load_games(name: str):
    fp = os.path.join(ROOT, name)
    if not os.path.exists(fp):
        return None
    return pd.read_parquet(fp)


@st.cache_data(ttl=3600)
def aicredits_rates():
    key = os.getenv("LLM_API_KEY") or ""
    model = os.getenv("LLM_MODEL") or "meta/muse-spark-1.3-contributor"
    if not key:
        return {"error": "LLM_API_KEY unset"}
    try:
        req = urllib.request.Request("https://api.aicredits.in/v1/models",
                                     headers={"Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=20) as r:
            items = json.loads(r.read().decode()).get("data", [])
        for m in items:
            if m.get("id") == model:
                return m
        return {"error": f"{model} not in catalog"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def aicredits_wallet():
    key = os.getenv("LLM_API_KEY") or ""
    if not key:
        return {"error": "LLM_API_KEY unset"}
    try:
        req = urllib.request.Request("https://api.aicredits.in/v1/credits",
                                     headers={"Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


st.set_page_config(page_title="Mafia Arena", layout="wide")
st.title("Mafia Arena — Thesis Dashboard")

tabs = st.tabs(["Run Status", "Costs", "Games", "Raw Logs", "Docs", "Config"])
if st.sidebar.button("Refresh data"):
    st.cache_data.clear()

with tabs[0]:
    st.subheader("Live run status")
    prog = load_progress()
    if prog.empty:
        st.info("No logs/progress.jsonl yet — runs with the telemetry patch append one line per game-day. "
                "Output parquets below still show finished games.")
    else:
        last = prog.iloc[-1]
        age = time.time() - float(last.get("ts", 0))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("State", "RUNNING" if age < 300 else " idle", f"last update {age:.0f}s ago")
        c2.metric("Run", str(last.get("run_id", "?")))
        c3.metric("Day", str(last.get("day", "?")))
        c4.metric("Alive", str(last.get("alive", "?")))
        st.dataframe(prog.tail(15), width="stretch")
    st.subheader("Output files")
    st.dataframe(list_outputs(), width="stretch")

with tabs[1]:
    st.subheader("Spend — LLM via OpenRouter/AiCredits, Jev gate")
    st.caption("LLM cost: AiCredits wallet (read-only) + manual calculation below "
               "(OpenRouter :free models cost 0). "
               "Jev uses OpenRouterJevAPIKey when set (no 1 req/min guard); "
               "otherwise the legacy BeatAI free-tier guard applies.")
    if st.button("Check AiCredits wallet now"):
        w = aicredits_wallet()
        st.json(w)
    st.caption("Wallet queried only on click (no auto-spend, read-only endpoint).")
    rates = aicredits_rates()
    if "error" in rates:
        st.warning(f"Rates lookup: {rates['error']}")
    else:
        st.write(f"Model **{rates.get('id')}** — in ₹/1M tokens: "
                 f"input {rates.get('input_cost_per_token_inr', 0)*1e6:.2f}, "
                 f"output {rates.get('output_cost_per_token_inr', 0)*1e6:.2f} "
                 f"(context {rates.get('context_length', '?')})")
    gfiles = sorted(glob.glob(os.path.join(ROOT, "logs", "games*.parquet")))
    if gfiles:
        name = os.path.relpath(st.selectbox("Games file", gfiles), ROOT)
        df = load_games(name)
        if df is not None and "est_cost_inr" in df.columns:
            c1, c2, c3 = st.columns(3)
            c1.metric("Games", len(df))
            c2.metric("Total est. LLM spend", f"Rs.{df['est_cost_inr'].sum():.2f}")
            c3.metric("Mean per game", f"Rs.{df['est_cost_inr'].mean():.2f}")
            st.bar_chart(df.set_index("game_id")["est_cost_inr"])
            st.dataframe(df[["game_id", "focal", "gate", "winner", "prompt_tokens",
                             "completion_tokens", "est_cost_inr", "jev_stub"]], width="stretch")
            if "jev_stub" in df.columns:
                st.write("Jev calls — real (False) vs rate-guard stub (True):",
                         df["jev_stub"].value_counts(dropna=False).to_dict())
        else:
            st.info("Selected file has no cost columns (written before telemetry patch).")
    else:
        st.info("No logs/games*.parquet yet.")
    st.subheader("Manual calculator (AiCredits rates)")
    r_in = st.number_input("Input Rs./1M tokens", value=9.53, format="%.2f")
    r_out = st.number_input("Output Rs./1M tokens", value=19.06, format="%.2f")
    p = st.number_input("Prompt tokens", value=147183, step=1000)
    c = st.number_input("Completion tokens", value=69310, step=1000)
    st.metric("Estimated cost", f"Rs.{(p * r_in + c * r_out) / 1e6:.2f}")
    st.caption("Defaults: catalog rates for meta/muse-spark-1.3-contributor (2026-10-14) "
               "and the measured game-1 totals. Same formula as run_arena `est_cost_inr`.")

with tabs[2]:
    st.subheader("Results")
    gfiles = sorted(glob.glob(os.path.join(ROOT, "logs", "games*.parquet")))
    if not gfiles:
        st.info("No games files yet — run: python -m src.eval.run_arena --games 2")
    else:
        name = os.path.relpath(st.selectbox("Games file ", gfiles, key="games_sel"), ROOT)
        df = load_games(name)
        if df is not None and len(df):
            st.bar_chart(df["winner"].value_counts())
            st.write("Winner share by focal:")
            st.dataframe(df.groupby("focal")["winner"].value_counts(normalize=True).round(2))
            st.dataframe(df, width="stretch")

with tabs[3]:
    st.subheader("Per-game histories")
    hfiles = sorted(glob.glob(os.path.join(ROOT, "logs", "raw", "history_*.parquet")))
    if not hfiles:
        st.info("No logs/raw/history_*.parquet yet.")
    else:
        fp = st.selectbox("History file", hfiles)
        try:
            h = pd.read_parquet(fp)
            st.write(f"{len(h)} events")
            st.dataframe(h, width="stretch")
        except Exception as e:
            st.error(str(e)[:300])

with tabs[4]:
    st.subheader("Thesis docs")
    docs = sorted(glob.glob(os.path.join(ROOT, "*.md")) + glob.glob(os.path.join(ROOT, "docs", "*.md")))
    pick = st.selectbox("Document", [os.path.relpath(d, ROOT) for d in docs])
    if pick:
        with open(os.path.join(ROOT, pick), encoding="utf-8", errors="replace") as f:
            st.markdown(f.read())

with tabs[5]:
    st.subheader("Active configuration (secrets masked)")
    st.json({
        "LLM": {"base_url": os.getenv("LLM_BASE_URL"), "model": os.getenv("LLM_MODEL"),
                "api_key": _masked("LLM_API_KEY"), "max_tokens": os.getenv("LLM_MAX_TOKENS")},
        "OpenRouter": {"model": os.getenv("OpenRouterModel"),
                       "api_key": _masked("OpenRouterAPIKey")},
        "JEV": {"base_url": os.getenv("OpenRouterJevBaseUrl") or os.getenv("JEV_BASE_URL"),
                "model": os.getenv("OpenRouterJevModel") or os.getenv("JEV_MODEL"),
                "api_key": (_masked("OpenRouterJevAPIKey") if os.getenv("OpenRouterJevAPIKey") else _masked("JEV_API_KEY")),
                "min_interval": os.getenv("JEV_MIN_INTERVAL_S", "0 with new key, else 61"),
                "jev_threshold": os.getenv("JEV_THRESHOLD", "0.6")},
        "thresholds": {"TAU_DELAY": os.getenv("TAU_DELAY"), "EVT_THRESHOLD": os.getenv("EVT_THRESHOLD"),
                       "temps": [os.getenv("LLM_TEMPERATURE_DIALOGUE"), os.getenv("LLM_TEMPERATURE_JSON")]},
    })
    st.caption("Last live-verified 2026-10-14: AiCredits chat_text/chat_json OK; "
               "BeatAI systemone noul/choice/score OK. Re-verify after the OpenRouter switch.")
