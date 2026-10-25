import re
from datetime import datetime

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b({MONTHS})\.? (\d{{1,2}})(?:st|nd|rd|th)?(?:,? (\d{{4}}))?", re.I)
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.I)


def parse_date(text, posted=None):
    """Find the first 'Month Day[, Year]' (+ optional 'H[:MM] am/pm') in text."""
    m = DATE_RE.search(text)
    if not m:
        return None
    posted = posted or datetime.now()
    month = datetime.strptime(m.group(1).title(), "%B").month
    year = int(m.group(3)) if m.group(3) else posted.year
    try:
        d = datetime(year, month, int(m.group(2)))
    except ValueError:
        return None
    if not m.group(3) and d.date() < posted.date():
        d = d.replace(year=year + 1)
    t = TIME_RE.search(text, m.end()) or TIME_RE.search(text)
    if t:
        hour = int(t.group(1)) % 12 + (12 if t.group(3).lower() == "pm" else 0)
        d = d.replace(hour=hour, minute=int(t.group(2) or 0))
    return d
