"""Regenerate the data baked into web/index.html from checklist.json + verdicts.json.

Run this whenever the pipeline produces new verdicts:
    python scripts/build_web.py

The website (web/index.html) is fully static — open it directly or serve it:
    python -m http.server 8765 --directory web
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "web" / "index.html"


def build_data():
    checklist = json.loads((ROOT / "checklist.json").read_text()) if (ROOT / "checklist.json").exists() else []
    verdicts = json.loads((ROOT / "verdicts.json").read_text()) if (ROOT / "verdicts.json").exists() else {}

    steps = []
    for r in checklist:
        rid = str(r.get("chapter_step_id") or r.get("step_id") or "?")
        v = verdicts.get(rid, {})
        steps.append({
            "id": rid,
            "ch": rid.split(".")[0] if "." in rid else "?",
            "action": (r.get("action") or "")[:120],
            "verdict": v.get("verdict", "Pending"),
            "confidence": v.get("confidence"),
            "ts": v.get("evidence_timestamp"),
            "note": (v.get("note") or "")[:200],
        })

    return {
        "run_id": "RUN-2026-06-15-001",
        "procedure": "STEMFIE Vehicle Assembly · Procedure A",
        "steps": steps,
    }


def main():
    data = build_data()
    payload = json.dumps(data, separators=(",", ":"))

    html = INDEX.read_text()
    new_html, n = re.subn(r"const DATA = .*?;\n",
                          lambda _: f"const DATA = {payload};\n", html, count=1)
    if n != 1:
        raise SystemExit("Could not find the `const DATA = ...;` line in web/index.html")
    INDEX.write_text(new_html)

    inspected = [s for s in data["steps"] if s["verdict"] != "Pending"]
    n_pass = sum(1 for s in inspected if s["verdict"] == "Compliant")
    score = round(100 * n_pass / len(inspected)) if inspected else 0
    print(f"Rebuilt web/index.html — {len(data['steps'])} steps, "
          f"{len(inspected)} inspected, adherence {score}%")


if __name__ == "__main__":
    main()
