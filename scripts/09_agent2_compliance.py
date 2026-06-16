#!/usr/bin/env python3
"""Agent 2 - Compliance Reasoning."""
import json, os, random, time
from pathlib import Path
from openai import OpenAI

gpt = OpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url=os.environ["GPT4O_BASE_URL"])
CHECKLIST_PATH = Path("checklist.json")
OBSERVATIONS_PATH = Path("mock_observations.json")
VERDICTS_PATH = Path("verdicts.json")

# FILTER: only verify action steps (Chapters 2-7), skip policy (Ch 1) and rework (Ch 8)
ACTION_CHAPTERS = {"2", "3", "4", "5", "6", "7"}

def filter_action_steps(checklist):
    out = []
    for r in checklist:
        csid = str(r.get("chapter_step_id", ""))
        ch = csid.split(".")[0] if "." in csid else ""
        if ch in ACTION_CHAPTERS:
            out.append(r)
    return out

def generate_mock_observations(checklist):
    rng = random.Random(42)
    obs = {}
    for i, rule in enumerate(checklist):
        rid = rule.get("chapter_step_id") or f"rule-{i}"
        roll = rng.random()
        components = rule.get("components_required") or ["unknown component"]
        action = rule.get("action", "perform step")
        ts_min = i // 4; ts_sec = (i * 17) % 60
        timestamp = f"00:{ts_min:02d}:{ts_sec:02d}"
        if roll < 0.70:
            o = {"timestamp": timestamp, "scene_description": f"Operator performs: {action.lower()}. Components visible: {', '.join(components[:3])}.",
                 "components_seen": components, "operator_action": action, "confidence": round(0.80 + rng.random() * 0.15, 2)}
        elif roll < 0.90:
            deviations = rule.get("deviation_patterns") or ["wrong component used"]
            chosen_dev = rng.choice(deviations)
            o = {"timestamp": timestamp, "scene_description": f"Operator attempts: {action.lower()}. Anomaly: {chosen_dev}",
                 "components_seen": components[:1] + ["WRONG_PART_X" + str(i)], "operator_action": f"deviation: {chosen_dev}",
                 "confidence": round(0.70 + rng.random() * 0.20, 2)}
        else:
            o = {"timestamp": timestamp, "scene_description": "Hands obscure work area. Action not clearly visible.",
                 "components_seen": [], "operator_action": "unclear", "confidence": round(0.30 + rng.random() * 0.25, 2)}
        obs[str(rid)] = o
    return obs

SYSTEM_PROMPT = """You are Agent 2, the compliance reasoning agent for ProcedureGuard.
You receive a single compliance rule and a video observation. Decide whether the
observation confirms compliance, shows a deviation, or is too unclear to verify.

Return ONLY valid JSON with these exact keys:
  chapter_step_id      -- copy from the input rule
  verdict              -- one of: "Compliant", "Deviation Detected", "Unable to Verify"
  confidence           -- a float between 0.0 and 1.0
  evidence_timestamp   -- copy the timestamp from the observation
  note                 -- one sentence explaining the verdict

Decision logic:
  - If observed components and action match the rule's acceptance_criterion -> Compliant
  - If observed components or action match any deviation_patterns -> Deviation Detected
  - If observation is unclear or low-confidence -> Unable to Verify

Return only the JSON object, no prose."""

def reason_about_step(rule, observation):
    user = f"COMPLIANCE RULE:\n{json.dumps(rule, indent=2)}\n\nVIDEO OBSERVATION:\n{json.dumps(observation, indent=2)}\n\nReturn the JSON verdict."
    resp = gpt.chat.completions.create(model="gpt-4o", messages=[
        {"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}
    ], temperature=0.1, response_format={"type": "json_object"})
    return json.loads(resp.choices[0].message.content)

def main():
    if not CHECKLIST_PATH.exists():
        raise SystemExit("checklist.json not found. Run Agent 1 first.")
    print(">> Loading checklist from Agent 1...")
    checklist = json.loads(CHECKLIST_PATH.read_text())
    print(f"   {len(checklist)} total rules loaded")
    checklist = filter_action_steps(checklist)
    print(f"   {len(checklist)} action steps after filtering (Chapters {sorted(ACTION_CHAPTERS)})")

    print("\n>> Generating mock video observations...")
    observations = generate_mock_observations(checklist)
    OBSERVATIONS_PATH.write_text(json.dumps(observations, indent=2))
    print(f"   wrote {OBSERVATIONS_PATH}")

    print(f"\n>> Reasoning about each step with GPT-4o (~{len(checklist)*7} seconds)...")
    verdicts = {}
    for i, rule in enumerate(checklist):
        rid = rule.get("chapter_step_id") or f"rule-{i}"
        obs = observations.get(str(rid))
        print(f"-- Verdict for Step {rid} ({rule.get('action','?')[:55]})...")
        try:
            v = reason_about_step(rule, obs)
            verdicts[str(rid)] = v
            print(f"   {v.get('verdict','?'):24}  conf={v.get('confidence',0):.2f}")
        except Exception as e:
            err = str(e)
            if "429" in err or "RateLimit" in err:
                print("   RATE LIMIT HIT - stopping. Saving partial verdicts.")
                break
            print(f"   ERROR: {err[:120]}")
        time.sleep(7)

    VERDICTS_PATH.write_text(json.dumps(verdicts, indent=2))
    print(f"\n[ok] wrote {VERDICTS_PATH} ({len(verdicts)} verdict(s))")
    counts = {"Compliant": 0, "Deviation Detected": 0, "Unable to Verify": 0}
    for v in verdicts.values():
        counts[v.get("verdict", "Unable to Verify")] = counts.get(v.get("verdict", "Unable to Verify"), 0) + 1
    total = sum(counts.values())
    print(f"\n========== SUMMARY ==========")
    print(f"  Total verified:        {total}")
    if total:
        print(f"  Compliant:             {counts['Compliant']:3d}  ({100*counts['Compliant']/total:.1f}%)")
        print(f"  Deviation Detected:    {counts['Deviation Detected']:3d}  ({100*counts['Deviation Detected']/total:.1f}%)")
        print(f"  Unable to Verify:      {counts['Unable to Verify']:3d}  ({100*counts['Unable to Verify']/total:.1f}%)")
        print(f"  Adherence score:       {100*counts['Compliant']/total:.0f}%")

if __name__ == "__main__":
    main()
