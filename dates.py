import re
from datetime import datetime

DATE_RE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4})(?:.*?(\d{1,2})(?::(\d{2}))?\s*(am|pm))?", re.I)


def parse_date(text):
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        d = datetime.strptime(m.group(1), "%B %d, %Y")
    except ValueError:
        return None
    if m.group(2):
        hour = int(m.group(2)) % 12 + (12 if m.group(4).lower() == "pm" else 0)
        d = d.replace(hour=hour, minute=int(m.group(3) or 0))
    return d
