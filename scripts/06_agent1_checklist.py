#!/usr/bin/env python3
"""Agent 1 v2 - STEMFIE-aware SOP Ingestion via GitHub Models GPT-4o."""
import json
import os
import re
import time

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import OpenAI

SEARCH = os.environ["SEARCH_ENDPOINT"]
KEY = os.environ["SEARCH_ADMIN_KEY"]
INDEX = os.environ["SEARCH_INDEX_NAME"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
BASE_URL = os.environ["GPT4O_BASE_URL"]

search_client = SearchClient(SEARCH, INDEX, AzureKeyCredential(KEY))
gpt = OpenAI(api_key=GITHUB_TOKEN, base_url=BASE_URL)

# Chapter starts with "N. Title" on its own line (e.g. "2. Front chassis assembly")
CHAPTER_RE = re.compile(r"^(\d+)\.\s+([A-Z][A-Za-z\-\s]+?)$", re.MULTILINE)
# Real step: "STEP N Title" followed by a real instruction (not dotted TOC line, not single number/state)
STEP_RE = re.compile(
    r"STEP\s+(\d+)\s+([A-Z][A-Za-z][^\n]{8,80})\n"  # title >= 10 chars
    r"((?:(?!STEP\s+\d+|^\d+\.\s+[A-Z]).){50,2000})",  # body >= 50 chars, doesn't start a new chapter
    re.DOTALL | re.MULTILINE,
)
# Lines that are dots-and-numbers (table of contents) -- skip
TOC_RE = re.compile(r"\.{3,}\s*\d+\s*$", re.MULTILINE)

def fetch_full_sop_text():
    results = search_client.search(search_text="*", select=["content"], top=1)
    for r in results:
        return r["content"]
    raise SystemExit("No SOP found in the index.")

def strip_toc(text):
    """Drop the table of contents section -- it's confusing the parser."""
    # TOC ends when we see "1. Introduction" on its own line (the actual chapter)
    m = re.search(r"\n\s*1\.\s+Introduction\s*\n", text)
    if m:
        return text[m.start():]
    return text

def split_into_steps(full_text):
    """Return list of {chapter_num, chapter_title, step_num, step_title, raw_text}."""
    cleaned = strip_toc(full_text)
    # Remove TOC dot-fill lines just in case
    cleaned = TOC_RE.sub("", cleaned)

    # Find chapter boundaries
    chapters = []
    for m in CHAPTER_RE.finditer(cleaned):
        chapters.append((m.start(), int(m.group(1)), m.group(2).strip()))
    if not chapters:
        return []

    # For each chapter, slice its text and find real STEP entries inside
    steps = []
    for i, (start, ch_num, ch_title) in enumerate(chapters):
        end = chapters[i + 1][0] if i + 1 < len(chapters) else len(cleaned)
        chapter_text = cleaned[start:end]
        for sm in STEP_RE.finditer(chapter_text):
            step_num = int(sm.group(1))
            step_title = sm.group(2).strip()
            body = sm.group(3).strip()
            # Skip steps with obviously broken titles ("STEP 1 . . . . . 4")
            if len(step_title) < 8 or step_title.count(".") > 3:
                continue
            steps.append({
                "chapter_num": ch_num,
                "chapter_title": ch_title,
                "step_num": step_num,
                "step_title": step_title,
                "raw_text": f"{step_title}\n{body}",
            })
    return steps

SYSTEM_PROMPT = """You are an SOP ingestion agent for ProcedureGuard. Convert each SOP
step into a structured compliance rule the downstream reasoning agent will use to
verify a video of a manufacturing assembly procedure.

Return ONLY valid JSON with these exact keys:
  chapter_step_id      -- string like "2.3" meaning Chapter 2 Step 3
  action               -- short imperative summary of what the operator must do
  check_type           -- one of: "presence", "sequence", "duration", "verification"
  components_required  -- list of strings (parts/tools the operator must use)
  acceptance_criterion -- one sentence describing how to verify the step is done right
  deviation_patterns   -- list of documented ways this step can be done wrong

IMPORTANT:
- Only return ONE JSON object per call.
- If the step is purely informational (e.g. "scope and application"), set check_type to "verification" and describe what the operator must understand.
- Use the chapter and step numbers I give you to set chapter_step_id.
- Do not invent numbers, components, or torque values that are not in the source text.

Return only the JSON object - no prose, no markdown."""

def make_rule(step):
    chapter_step_id = f"{step['chapter_num']}.{step['step_num']}"
    user = (
        f"Chapter {step['chapter_num']}: {step['chapter_title']}\n"
        f"Step {chapter_step_id} - {step['step_title']}\n\n"
        f"Source text:\n{step['raw_text']}\n\n"
        f"Set chapter_step_id to \"{chapter_step_id}\" and return the JSON rule."
    )
    resp = gpt.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

def main():
    print(">> Fetching SOP from Azure AI Search...")
    full_text = fetch_full_sop_text()
    print(f"   got {len(full_text)} chars")

    steps = split_into_steps(full_text)
    print(f">> Found {len(steps)} valid step(s) across chapters")
    by_chapter = {}
    for s in steps:
        by_chapter.setdefault(s["chapter_num"], []).append(s["step_num"])
    for ch in sorted(by_chapter):
        print(f"   Chapter {ch}: steps {by_chapter[ch]}")

    checklist = []
    for s in steps:
        csid = f"{s['chapter_num']}.{s['step_num']}"
        print(f"-- Generating rule for Step {csid} ({s['step_title'][:55]})...")
        try:
            rule = make_rule(s)
            checklist.append(rule)
        except Exception as e:
            print(f"   ERROR: {e}")
        time.sleep(7)  # 10 req/min rate limit

    out = "results/checklist.json"
    with open(out, "w") as f:
        json.dump(checklist, f, indent=2)
    print(f"\n[ok] wrote {out}  ({len(checklist)} rule(s))")
    print(f"\n========== CHECKLIST SUMMARY ==========")
    for r in checklist:
        print(f"  {r.get('chapter_step_id','?')}: {r.get('action','?')[:80]}")

if __name__ == "__main__":
    main()
