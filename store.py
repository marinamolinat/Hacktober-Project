"""Data access for the 11-table schema in snowflake/002_schema.sql."""
import hashlib
import json
import re
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import db

DEFAULT_TZ = "America/Indiana/Indianapolis"
HANDLE_RE = re.compile(r"^[a-z0-9._]{1,30}$")
EXTRACTION_VERSION = "events-v1:heuristic-or-cortex:prompt-v1"


def new_id():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def iso(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value.isoformat()


def as_dt(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def as_date(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def as_json(value):
    return json.loads(value) if isinstance(value, str) else value


def normalize_handle(raw):
    handle = raw.strip()
    handle = handle[1:] if handle.startswith("@") else handle
    handle = handle.lower()
    return handle if HANDLE_RE.match(handle) else None


# Users -------------------------------------------------------------------

def get_user_by_email(email):
    return db.one(
        "SELECT USER_ID, EMAIL, PASSWORD_HASH, DISPLAY_NAME, TIMEZONE FROM USERS "
        "WHERE EMAIL = %s AND DELETED_AT IS NULL", (email,))


def get_user(user_id):
    return db.one(
        "SELECT USER_ID, EMAIL, DISPLAY_NAME, TIMEZONE FROM USERS "
        "WHERE USER_ID = %s AND DELETED_AT IS NULL", (user_id,))


def create_user(email, password_hash, display_name=None):
    """Creates USERS + default USER_PREFERENCES in one transaction (§2.1)."""
    user_id, ts = new_id(), now()
    with db.transaction():
        if db.one("SELECT USER_ID FROM USERS WHERE EMAIL = %s", (email,)):
            return None
        db.query(
            "INSERT INTO USERS (USER_ID, AUTH_SUBJECT, EMAIL, PASSWORD_HASH, DISPLAY_NAME, TIMEZONE, CREATED_AT, UPDATED_AT) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, f"local:{email}", email, password_hash, display_name, DEFAULT_TZ, ts, ts))
        db.query(
            "INSERT INTO USER_PREFERENCES (USER_ID, PREFERENCE_TEXT, INTEREST_TAG_IDS, EXCLUDED_TAG_IDS, "
            "FOLLOWED_ONLY, FREE_ONLY, HORIZON_DAYS, VERSION, UPDATED_AT) "
            "SELECT %s, '', TO_ARRAY(PARSE_JSON('[]')), TO_ARRAY(PARSE_JSON('[]')), FALSE, FALSE, 30, 1, %s",
            (user_id, ts))
    return user_id


def get_preferences(user_id):
    return db.one("SELECT HORIZON_DAYS, FOLLOWED_ONLY, VERSION FROM USER_PREFERENCES WHERE USER_ID = %s", (user_id,))


# Accounts and follows ----------------------------------------------------

def get_or_create_account(username):
    with db.transaction():
        row = db.one("SELECT ACCOUNT_ID, USERNAME, INGESTION_STATUS FROM INSTAGRAM_ACCOUNTS WHERE USERNAME = %s", (username,))
        if row:
            return row
        account_id, ts = new_id(), now()
        db.query(
            "INSERT INTO INSTAGRAM_ACCOUNTS (ACCOUNT_ID, USERNAME, PROFILE_URL, IS_ACTIVE, INGESTION_STATUS, CREATED_AT, UPDATED_AT) "
            "VALUES (%s, %s, %s, TRUE, 'pending', %s, %s)",
            (account_id, username, f"https://www.instagram.com/{username}/", ts, ts))
        return {"account_id": account_id, "username": username, "ingestion_status": "pending"}


def follow(user_id, account_id):
    """Returns True if the follow was new."""
    with db.transaction():
        if db.one("SELECT 1 AS X FROM USER_FOLLOWS WHERE USER_ID = %s AND ACCOUNT_ID = %s", (user_id, account_id)):
            return False
        db.query("INSERT INTO USER_FOLLOWS (USER_ID, ACCOUNT_ID, CREATED_AT) VALUES (%s, %s, %s)", (user_id, account_id, now()))
        return True


def unfollow(user_id, account_id):
    db.query("DELETE FROM USER_FOLLOWS WHERE USER_ID = %s AND ACCOUNT_ID = %s", (user_id, account_id))


def list_follows(user_id):
    rows = db.query(
        "SELECT a.ACCOUNT_ID, a.USERNAME, a.CLUB_ID, a.INGESTION_STATUS, a.LAST_SUCCESS_AT, a.LAST_ERROR "
        "FROM USER_FOLLOWS f JOIN INSTAGRAM_ACCOUNTS a ON a.ACCOUNT_ID = f.ACCOUNT_ID "
        "WHERE f.USER_ID = %s ORDER BY a.USERNAME", (user_id,))
    for r in rows:
        r["last_success_at"] = iso(r["last_success_at"])
    return rows


def set_ingestion_state(account_id, status, error=None, success=False):
    ts = now()
    db.query(
        "UPDATE INSTAGRAM_ACCOUNTS SET INGESTION_STATUS = %s, LAST_ERROR = %s, LAST_ATTEMPT_AT = %s, "
        "LAST_SUCCESS_AT = CASE WHEN %s THEN %s ELSE LAST_SUCCESS_AT END, UPDATED_AT = %s WHERE ACCOUNT_ID = %s",
        (status, (error or "")[:2000] or None, ts, success, ts, ts, account_id))


def club_for_account(account_id):
    """Every account is its own club; created on first use."""
    with db.transaction():
        row = db.one(
            "SELECT c.CLUB_ID, c.NAME, a.USERNAME FROM INSTAGRAM_ACCOUNTS a LEFT JOIN CLUBS c ON c.CLUB_ID = a.CLUB_ID "
            "WHERE a.ACCOUNT_ID = %s", (account_id,))
        if row["club_id"]:
            return {"club_id": row["club_id"], "name": row["name"]}
        club = db.one("SELECT CLUB_ID, NAME FROM CLUBS WHERE SLUG = %s", (row["username"],))
        ts = now()
        if not club:
            club = {"club_id": new_id(), "name": row["username"]}
            db.query(
                "INSERT INTO CLUBS (CLUB_ID, SLUG, NAME, IS_ACTIVE, CREATED_AT, UPDATED_AT) "
                "VALUES (%s, %s, %s, TRUE, %s, %s)", (club["club_id"], row["username"], row["username"], ts, ts))
        db.query("UPDATE INSTAGRAM_ACCOUNTS SET CLUB_ID = %s, UPDATED_AT = %s WHERE ACCOUNT_ID = %s",
                 (club["club_id"], ts, account_id))
        return club


# Posts -------------------------------------------------------------------

def post_id_for(shortcode):
    return sha256(f"instagram:post:{shortcode}")


def upsert_post(account_id, p):
    """Idempotent per shortcode + content hash (§3.1). Returns inserted/updated/unchanged."""
    post_id = post_id_for(p["shortcode"])
    content_hash = sha256(canonical({"caption": p["caption"], "shortcode": p["shortcode"], "ocr_text": None}))
    media = canonical([p["image"]] if p.get("image") else [])
    ts = now()
    with db.transaction():
        row = db.one("SELECT CONTENT_HASH FROM POSTS WHERE POST_ID = %s", (post_id,))
        if row and row["content_hash"] == content_hash:
            db.query("UPDATE POSTS SET SOURCE_SEEN_AT = %s, MEDIA_URLS = TO_ARRAY(PARSE_JSON(%s)) WHERE POST_ID = %s",
                     (ts, media, post_id))
            return "unchanged"
        if row:
            db.query(
                "UPDATE POSTS SET CAPTION = %s, MEDIA_URLS = TO_ARRAY(PARSE_JSON(%s)), CONTENT_HASH = %s, "
                "EXTRACTION_STATUS = 'pending', ATTEMPT_COUNT = 0, SOURCE_SEEN_AT = %s, UPDATED_AT = %s WHERE POST_ID = %s",
                (p["caption"], media, content_hash, ts, ts, post_id))
            return "updated"
        db.query(
            "INSERT INTO POSTS (POST_ID, SHORTCODE, ACCOUNT_ID, PERMALINK, POSTED_AT, CAPTION, MEDIA_TYPE, MEDIA_URLS, "
            "CONTENT_HASH, EXTRACTION_STATUS, ATTEMPT_COUNT, INGESTED_AT, SOURCE_SEEN_AT, UPDATED_AT) "
            "SELECT %s, %s, %s, %s, %s, %s, %s, TO_ARRAY(PARSE_JSON(%s)), %s, 'pending', 0, %s, %s, %s",
            (post_id, p["shortcode"], account_id, p["url"], p["timestamp"], p["caption"], p["media_type"], media,
             content_hash, ts, ts, ts))
        return "inserted"


def pending_posts(account_id):
    return db.query(
        "SELECT POST_ID, CAPTION, POSTED_AT, CONTENT_HASH FROM POSTS "
        "WHERE ACCOUNT_ID = %s AND EXTRACTION_STATUS = 'pending' AND DELETED_AT IS NULL", (account_id,))


def save_extraction(post_id, content_hash, payload, error=None):
    db.query(
        "UPDATE POSTS SET EXTRACTION_STATUS = %s, EXTRACTION_VERSION = %s, EXTRACTED_PAYLOAD = PARSE_JSON(%s), "
        "ATTEMPT_COUNT = ATTEMPT_COUNT + 1, LAST_ERROR = %s, UPDATED_AT = %s WHERE POST_ID = %s AND CONTENT_HASH = %s",
        ("failed" if error else "processed", EXTRACTION_VERSION, canonical(payload), error, now(), post_id, content_hash))


# Events ------------------------------------------------------------------

def _dedupe_key(club_id, local_date, local_time, title):
    title = " ".join(unicodedata.normalize("NFC", title).lower().split())
    return sha256(canonical({"club_id": club_id, "local_start_date": local_date,
                             "local_start_time": local_time or "date-only", "normalized_title": title}))


def sync_events(account_id):
    """Publish events from processed posts of an account (§2.5, §3.2)."""
    posts = db.query(
        "SELECT POST_ID, CONTENT_HASH, EXTRACTED_PAYLOAD FROM POSTS WHERE ACCOUNT_ID = %s "
        "AND EXTRACTION_STATUS = 'processed' AND DELETED_AT IS NULL", (account_id,))
    if not any((as_json(p["extracted_payload"]) or {}).get("events") for p in posts):
        return 0
    club = club_for_account(account_id)
    created = 0
    for post in posts:
        for ev in (as_json(post["extracted_payload"]) or {}).get("events", []):
            created += _upsert_event(club, post, ev)
    return created


def _upsert_event(club, post, ev):
    if not ev.get("title") or not ev.get("local_start_date"):
        return 0
    tz = ZoneInfo(ev.get("event_timezone") or DEFAULT_TZ)
    local_time = ev.get("local_start_time")
    local = datetime.fromisoformat(f"{ev['local_start_date']}T{local_time or '00:00'}").replace(tzinfo=tz)
    start_at = local.astimezone(timezone.utc).isoformat()
    precision = "exact" if local_time else "date_only"
    key = _dedupe_key(club["club_id"], ev["local_start_date"], local_time, ev["title"])
    search_text = " | ".join(filter(None, [ev["title"], ev.get("description"), club["name"],
                                           ev["local_start_date"], local_time or "time not announced", ev.get("location_name")]))
    ts = now()
    with db.transaction():
        row = db.one("SELECT EVENT_ID FROM EVENTS WHERE DEDUPE_KEY = %s", (key,))
        event_id = row["event_id"] if row else new_id()
        if not row:
            db.query(
                "INSERT INTO EVENTS (EVENT_ID, DEDUPE_KEY, CLUB_ID, TITLE, DESCRIPTION, START_AT, LOCAL_START_DATE, "
                "EVENT_TIMEZONE, DATE_PRECISION, LOCATION_NAME, PRICE_CURRENCY, STATUS, EXTRACTION_VERSION, "
                "SEARCH_TEXT, REVISION, CREATED_AT, UPDATED_AT) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'USD', 'published', %s, %s, 1, %s, %s)",
                (event_id, key, club["club_id"], ev["title"], ev.get("description"), start_at, ev["local_start_date"],
                 str(tz), precision, ev.get("location_name"), EXTRACTION_VERSION, search_text, ts, ts))
        if not db.one("SELECT 1 AS X FROM EVENT_SOURCES WHERE EVENT_ID = %s AND POST_ID = %s", (event_id, post["post_id"])):
            has_primary = db.one("SELECT 1 AS X FROM EVENT_SOURCES WHERE EVENT_ID = %s AND IS_PRIMARY", (event_id,))
            db.query(
                "INSERT INTO EVENT_SOURCES (EVENT_ID, POST_ID, SOURCE_EVENT_KEY, IS_PRIMARY, EVIDENCE, SOURCE_CONTENT_HASH, "
                "EXTRACTION_VERSION, CREATED_AT, UPDATED_AT) SELECT %s, %s, %s, %s, PARSE_JSON(%s), %s, %s, %s, %s",
                (event_id, post["post_id"], new_id(), not has_primary, canonical(ev.get("evidence") or {}),
                 post["content_hash"], EXTRACTION_VERSION, ts, ts))
    return 0 if row else 1


# Feeds -------------------------------------------------------------------

def newsletter(user_id, days=7, limit=20):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = db.query(
        "SELECT p.POST_ID, p.CAPTION, p.POSTED_AT, p.PERMALINK, p.MEDIA_URLS, p.EXTRACTED_PAYLOAD, a.USERNAME "
        "FROM POSTS p JOIN USER_FOLLOWS f ON f.ACCOUNT_ID = p.ACCOUNT_ID AND f.USER_ID = %s "
        "JOIN INSTAGRAM_ACCOUNTS a ON a.ACCOUNT_ID = p.ACCOUNT_ID "
        "WHERE p.DELETED_AT IS NULL AND p.POSTED_AT >= %s ORDER BY p.POSTED_AT DESC, p.POST_ID LIMIT %s",
        (user_id, since, limit))
    return [{
        "post_id": r["post_id"], "account": r["username"], "caption": r["caption"],
        "posted_at": iso(r["posted_at"]), "permalink": r["permalink"], "media_urls": as_json(r["media_urls"]) or [],
        "summary": (as_json(r["extracted_payload"]) or {}).get("summary"),
    } for r in rows]


def events_feed(user_id, limit=20):
    """Simplified §6.1: published events with a live primary source, date-gated,
    score = 50*F + 5*U (no tags/search yet), tie-break START_AT, EVENT_ID."""
    prefs = get_preferences(user_id) or {"horizon_days": 30, "followed_only": False}
    rows = db.query(
        "SELECT e.EVENT_ID, e.TITLE, e.DESCRIPTION, e.START_AT, e.END_AT, e.LOCAL_START_DATE, e.EVENT_TIMEZONE, "
        "e.DATE_PRECISION, e.LOCATION_NAME, e.IS_FREE, e.PRICE_AMOUNT, e.PRICE_CURRENCY, e.REGISTRATION_URL, "
        "e.STATUS, e.UPDATED_AT, c.CLUB_ID, c.NAME AS CLUB_NAME, s.POST_ID, p.PERMALINK, s.IS_PRIMARY, "
        "CASE WHEN EXISTS (SELECT 1 FROM USER_FOLLOWS f JOIN INSTAGRAM_ACCOUNTS a ON a.ACCOUNT_ID = f.ACCOUNT_ID "
        "  WHERE f.USER_ID = %s AND (a.CLUB_ID = e.CLUB_ID OR a.ACCOUNT_ID = p.ACCOUNT_ID)) THEN 1 ELSE 0 END AS FOLLOWED "
        "FROM EVENTS e JOIN CLUBS c ON c.CLUB_ID = e.CLUB_ID AND c.IS_ACTIVE "
        "JOIN EVENT_SOURCES s ON s.EVENT_ID = e.EVENT_ID JOIN POSTS p ON p.POST_ID = s.POST_ID AND p.DELETED_AT IS NULL "
        "WHERE e.STATUS = 'published' AND e.DATE_PRECISION <> 'unknown'", (user_id,))
    now_utc = datetime.now(timezone.utc)
    events = {}
    for r in rows:
        ev = events.setdefault(r["event_id"], {**r, "sources": []})
        ev["sources"].append({"post_id": r["post_id"], "url": r["permalink"], "is_primary": bool(r["is_primary"])})
    items = []
    for ev in events.values():
        if not any(s["is_primary"] for s in ev["sources"]):
            continue
        tz = ZoneInfo(ev["event_timezone"])
        today = now_utc.astimezone(tz).date()
        local_date = as_date(ev["local_start_date"])
        start = as_dt(ev["start_at"])
        upcoming = start >= now_utc if ev["date_precision"] == "exact" else local_date >= today
        days_until = (local_date - today).days
        if not upcoming or days_until > prefs["horizon_days"] or (prefs["followed_only"] and not ev["followed"]):
            continue
        score = 50 * ev["followed"] + 5 * (1 / (1 + days_until))
        items.append((-score, iso(start), ev["event_id"], {
            "event_id": ev["event_id"], "club": {"club_id": ev["club_id"], "name": ev["club_name"]},
            "title": ev["title"], "description": ev["description"], "start_at": iso(start), "end_at": iso(ev["end_at"]),
            "local_start_date": local_date.isoformat(), "event_timezone": ev["event_timezone"],
            "date_precision": ev["date_precision"], "location_name": ev["location_name"],
            "is_free": None if ev["is_free"] is None else bool(ev["is_free"]),
            "price_amount": None if ev["price_amount"] is None else f"{float(ev['price_amount']):.2f}",
            "price_currency": ev["price_currency"], "registration_url": ev["registration_url"], "tags": [],
            "status": ev["status"], "reasons": ["followed_account", "upcoming"] if ev["followed"] else ["upcoming"],
            "source_posts": ev["sources"], "updated_at": iso(ev["updated_at"]),
        }))
    items.sort(key=lambda t: t[:3])
    return [t[3] for t in items[:limit]]
