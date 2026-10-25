import os
import random
import json
import re
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path

import requests

APIFY_URL = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items"


def scrape(usernames, limit=None):
    limit = limit or int(os.getenv("POSTS_PER_USER", "8"))
    backend = os.getenv("SCRAPER") or ("apify" if os.getenv("APIFY_TOKEN") else "instaloader")
    fetch = {"instaloader": instaloader_posts, "apify": apify_posts, "cached": cached_posts, "mock": mock_posts}.get(backend)
    if fetch is None:
        raise ValueError("Choose instaloader, apify, or cached for SCRAPER.")
    posts = [p for p in fetch(usernames, limit) if not p.pop("pinned", False)]
    return sorted(posts, key=lambda p: p["timestamp"] or "", reverse=True)


def instaloader_posts(usernames, limit):
    import instaloader

    loader = instaloader.Instaloader(download_videos=False, save_metadata=False, max_connection_attempts=1, request_timeout=12)
    ig_user = os.getenv("IG_USERNAME")
    if ig_user:
        # Create once with: instaloader --login <IG_USERNAME>
        loader.load_session_from_file(ig_user, os.getenv("IG_SESSIONFILE") or None)
    posts = []
    for u in usernames:
        u = _handle(u)
        try:
            # The public-page path avoids the login-gated profile GraphQL endpoint.
            page = loader.context.get_page_data(u + "/")
            found = {}
            for node in _nodes(page):
                normalized = _normalize(node, u)
                if normalized:
                    found[normalized["shortcode"]] = normalized
            if not found:
                raise RuntimeError("Instagram did not return readable public posts.")
            posts.extend(sorted(found.values(), key=lambda item: item["timestamp"], reverse=True)[:limit])
        except Exception as exc:
            cached = cached_posts([u], limit)
            if not cached:
                raise RuntimeError(f"@{u}: public Instagram posts are unavailable; no previously captured posts exist.") from exc
            for post in cached:
                post["ingestion_warning"] = "Instagram is currently unavailable; showing previously captured public posts."
            posts.extend(cached)
    return posts


def _handle(value):
    handle = str(value).strip().lstrip("@").lower()
    if not re.fullmatch(r"[a-z0-9._]{1,30}", handle):
        raise ValueError("Enter Instagram handles, without profile URLs.")
    return handle


def _nodes(value):
    if isinstance(value, dict):
        if value.get("code") or value.get("shortcode"):
            yield value
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nodes(child)


def _normalize(node, username):
    owner = node.get("user") or node.get("owner") or {}
    if not isinstance(owner, dict) or owner.get("username", "").lower() != username:
        return None
    caption = node.get("caption")
    if isinstance(caption, dict):
        caption = caption.get("text", "")
    if not caption:
        edges = node.get("edge_media_to_caption", {}).get("edges", [])
        caption = edges[0].get("node", {}).get("text", "") if edges else ""
    timestamp = node.get("taken_at") or node.get("taken_at_timestamp")
    precision = "exact"
    if timestamp:
        timestamp = datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat()
    else:
        match = re.search(r" on ([A-Z][a-z]+ \d{1,2}, \d{4})", node.get("accessibility_caption", ""))
        if not match:
            return None
        timestamp = datetime.strptime(match.group(1), "%B %d, %Y").replace(tzinfo=timezone.utc).isoformat()
        precision = "date_only"
    shortcode = node.get("code") or node.get("shortcode")
    return {"username": username, "shortcode": shortcode, "caption": caption or "", "image": None,
            "url": f"https://www.instagram.com/p/{shortcode}/", "timestamp": timestamp,
            "timestamp_precision": precision, "media_type": {1: "image", 2: "video", 8: "carousel"}.get(node.get("media_type"), "image"),
            "source_mode": "live", "pinned": bool(node.get("is_pinned", False))}


def cached_posts(usernames, limit):
    path = Path(__file__).parent / "data" / "instagram_posts.json"
    if not path.exists():
        return []
    records = json.loads(path.read_text())
    result = []
    for username in usernames:
        username = _handle(username)
        items = [dict(item) for item in records if item.get("username") == username]
        result.extend(sorted(items, key=lambda item: item.get("timestamp", ""), reverse=True)[:limit])
    return result


def apify_posts(usernames, limit):
    resp = requests.post(
        APIFY_URL,
        params={"token": os.getenv("APIFY_TOKEN")},
        json={"username": usernames, "resultsLimit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    return [
        {
            "username": p.get("ownerUsername"),
            "caption": p.get("caption") or "",
            "image": p.get("displayUrl"),
            "url": p.get("url"),
            "timestamp": p.get("timestamp"),
            "pinned": p.get("isPinned", False),
            "source_mode": "live",
        }
        for p in resp.json()
    ]


MOCK_CAPTIONS = [
    "Join us for our Spring Mixer on {date} at 7pm in the Student Center! Free pizza 🍕",
    "Huge thanks to everyone who came out last week. Photos are up!",
    "Workshop alert: Intro to Python on {date} at 5pm, Room 204. Bring a laptop.",
    "Meet our new board members for this year 💙",
    "Hackathon kickoff {date} at 9am in the Engineering Hall. Prizes, swag, food.",
]


def mock_posts(usernames, limit):
    now = datetime.now(timezone.utc)
    rng = random.Random(",".join(usernames))
    posts = []
    for u in usernames:
        for i in range(min(limit, len(MOCK_CAPTIONS))):
            event_day = (now + timedelta(days=rng.randint(1, 25))).strftime("%B %d, %Y")
            posts.append({
                "username": u,
                "caption": MOCK_CAPTIONS[(i + len(u)) % len(MOCK_CAPTIONS)].format(date=event_day),
                "image": f"https://picsum.photos/seed/{u}{i}/400/400",
                "url": f"https://instagram.com/{u}",
                "timestamp": (now - timedelta(days=i)).isoformat(),
                "source_mode": "fixture",
            })
    return posts
