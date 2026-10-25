import json
import os
import re
from datetime import datetime

from dates import parse_date


def _snowflake_conn():
    if not os.getenv("SNOWFLAKE_ACCOUNT"):
        return None
    import snowflake.connector

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


PROMPT = """You read an Instagram post caption. Reply with ONLY JSON:
{{"summary": "<one sentence newsletter blurb>",
  "event": null or {{"title": "...", "start": "YYYY-MM-DDTHH:MM", "location": "..."}}}}
Only include an event if the post announces a specific upcoming event with a date.
Caption: {caption}"""


def analyze(posts):
    conn = _snowflake_conn()
    try:
        for p in posts:
            p.update(_cortex(conn, p["caption"]) if conn else _heuristic(p["caption"]))
    finally:
        if conn:
            conn.close()
    return posts


def _cortex(conn, caption):
    model = os.getenv("CORTEX_MODEL", "mistral-large2")
    cur = conn.cursor()
    cur.execute("SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s)", (model, PROMPT.format(caption=caption)))
    text = cur.fetchone()[0]
    match = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(match.group(0)) if match else _heuristic(caption)
    except json.JSONDecodeError:
        return _heuristic(caption)


def _heuristic(caption):
    summary = re.split(r"(?<=[.!?])\s", caption.strip(), maxsplit=1)[0]
    start = parse_date(caption)
    event = None
    if start and start > datetime.now():
        location = re.search(r"Room \d+|(?:[A-Z]\w* )+(?:Center|Hall)", caption)
        title = re.split(r"\s+(?:on\s+)?[A-Z][a-z]+ \d{1,2}, \d{4}", caption, maxsplit=1)[0]
        event = {
            "title": title.strip(" :,")[:60],
            "start": start.strftime("%Y-%m-%dT%H:%M"),
            "location": location.group(0) if location else "",
        }
    return {"summary": summary, "event": event}
