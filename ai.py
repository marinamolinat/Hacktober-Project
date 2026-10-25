import json
import os
import re
from datetime import datetime

import db
from dates import parse_date

DEFAULT_TZ = "America/Indiana/Indianapolis"

PROMPT = """You read an Instagram post caption from a Purdue club. Reply with ONLY JSON:
{{"summary": "<one sentence newsletter blurb>",
  "events": [{{"title": "...", "local_start_date": "YYYY-MM-DD", "local_start_time": "HH:MM" or null,
              "location_name": "..." or null, "evidence": {{"start": [{{"kind": "caption", "quote": "<exact text>"}}]}}}}]}}
"events" is [] unless the post announces a specific event with a date. Post date: {posted}.
Caption: {caption}"""


def extract(caption, posted_at=None):
    """Returns {"summary", "events": [...], "warnings": [...]} (specs.md §3.2 subset)."""
    model = os.getenv("SNOWFLAKE_EXTRACT_MODEL")
    if db.using_snowflake() and model:
        try:
            return _cortex(model, caption, posted_at)
        except Exception as e:
            result = _heuristic(caption, posted_at)
            result["warnings"].append(f"cortex_failed: {e}"[:300])
            return result
    return _heuristic(caption, posted_at)


def _cortex(model, caption, posted_at):
    row = db.one("SELECT AI_COMPLETE(%s, %s) AS R", (model, PROMPT.format(caption=caption, posted=posted_at)))
    text = row["r"] if isinstance(row["r"], str) else json.dumps(row["r"])
    data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    events = [{**e, "event_timezone": DEFAULT_TZ, "date_precision": "exact" if e.get("local_start_time") else "date_only"}
              for e in data.get("events") or [] if e.get("title") and e.get("local_start_date")]
    return {"summary": data.get("summary"), "events": events, "warnings": ["caption_only: images not read"]}


def _heuristic(caption, posted_at=None):
    first_line = caption.strip().split("\n", 1)[0]
    summary = re.split(r"(?<=[.!?])\s", first_line, maxsplit=1)[0]
    posted = datetime.fromisoformat(posted_at.replace("Z", "+00:00")).replace(tzinfo=None) if posted_at else None
    start = parse_date(caption, posted)
    events = []
    if start:
        location = re.search(r"📍\s*(.+)", caption) or re.search(r"Room \d+|(?:[A-Z]\w* )+(?:Center|Hall)", caption)
        title = re.split(r"\s+(?:on\s+)?[A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4}", summary, maxsplit=1)[0]
        events.append({
            "title": title.strip(" :,!")[:60],
            "local_start_date": start.strftime("%Y-%m-%d"),
            "local_start_time": start.strftime("%H:%M") if start.hour else None,
            "event_timezone": DEFAULT_TZ,
            "date_precision": "exact" if start.hour else "date_only",
            "location_name": (location.group(1) if location.groups() else location.group(0)).strip() if location else None,
            "evidence": {},
        })
    return {"summary": summary, "events": events, "warnings": ["heuristic_extractor: caption_only"]}
