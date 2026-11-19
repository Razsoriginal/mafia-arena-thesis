"""D-010 / D-013: gateway cutoff forensics from raw attempt rows. Nuisance
fields only (latency, error class, tokens); no game or episode outcome.

    .venv/bin/python -m src.explore.latency_forensics

Writes logs/explore/d010_latency.json.
"""
import collections
import glob
import json
import os
import statistics as st

RUNS = {"mvp-team-01-cal": "logs/runs/mvp-team-01-cal/raw/*/llm_raw.jsonl",
        "explore-ops-01": "logs/runs/explore-ops-01/raw/*/llm_raw.jsonl",
        "explore-ops-02-minimal": "logs/runs/explore-ops-02-minimal/raw/*/llm_raw.jsonl"}


def _rows(pattern):
    out = []
    for f in sorted(glob.glob(pattern)):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out


def summarise(rows):
    ok = [r for r in rows if not r.get("error_class") and r.get("latency_s") is not None]
    e500 = [r for r in rows if r.get("error_class") == "http_500" and r.get("latency_s") is not None]
    emp = [r for r in rows if r.get("error_class") == "empty_content"]
    band = lambda lo, hi: [r for r in ok if lo <= r["latency_s"] < hi]  # noqa: E731

    def tps(v):
        v = [r["completion_tokens"] / r["latency_s"] for r in v if r["latency_s"] > 0]
        return round(st.median(v), 1) if v else None

    hist = collections.Counter(min(int(r["latency_s"] // 5) * 5, 130) for r in ok)
    return {
        "attempt_rows": len(rows),
        "error_classes": dict(collections.Counter(str(r.get("error_class")) for r in rows)),
        "realised_models_ok": dict(collections.Counter(str(r.get("realised_model")) for r in ok)),
        "sdk_max_retries_logged": sorted({str(r.get("sdk_max_retries")) for r in rows}),
        "ok_latency_hist_5s": {str(k): v for k, v in sorted(hist.items())},
        "ok_n_under_35s": len(band(0, 35)), "ok_n_35_40s": len(band(35, 40)), "ok_n_40_65s": len(band(40, 65)),
        "ok_n_65_80s": len(band(65, 80)), "ok_n_80_95s": len(band(80, 95)),
        "ok_max_latency_s": round(max((r["latency_s"] for r in ok), default=0), 2),
        "tokens_per_s_median": {"under_25s": tps(band(0, 25)), "35_60s": tps(band(35, 60)),
                                "60_95s": tps(band(60, 95)), "all": tps(ok)},
        "http500_n": len(e500),
        "http500_n_90_100s": sum(1 for r in e500 if 90 <= r["latency_s"] < 100),
        "http500_latency_median_s": round(st.median(r["latency_s"] for r in e500), 2) if e500 else None,
        "http500_latency_min_s": round(min((r["latency_s"] for r in e500), default=0), 2) if e500 else None,
        "http500_latency_max_s": round(max((r["latency_s"] for r in e500), default=0), 2) if e500 else None,
        "empty_content_n": len(emp),
        "empty_content_cost_inr": round(sum(float(r.get("cost_inr") or 0) for r in emp), 2),
        "total_cost_inr": round(sum(float(r.get("cost_inr") or 0) for r in rows), 2),
    }


def main():
    out = {name: summarise(_rows(pat)) for name, pat in RUNS.items() if glob.glob(pat)}
    os.makedirs("logs/explore", exist_ok=True)
    with open("logs/explore/d010_latency.json", "w") as f:
        json.dump(out, f, indent=1)
    for name, s in out.items():
        print(name, "rows", s["attempt_rows"], "500s", s["http500_n"], "median 500 latency", s["http500_latency_median_s"],
              "ok max", s["ok_max_latency_s"], "tok/s", s["tokens_per_s_median"]["all"])


if __name__ == "__main__":
    main()
