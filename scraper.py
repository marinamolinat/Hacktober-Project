import os
import random
from datetime import datetime, timedelta, timezone
from itertools import islice

import requests

APIFY_URL = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items"


def scrape(usernames, limit=None):
    limit = limit or int(os.getenv("POSTS_PER_USER", "8"))
    backend = os.getenv("SCRAPER") or ("apify" if os.getenv("APIFY_TOKEN") else "mock")
    fetch = {"instaloader": instaloader_posts, "apify": apify_posts}.get(backend, mock_posts)
    posts = [p for p in fetch(usernames, limit) if not p.pop("pinned", False)]
    return sorted(posts, key=lambda p: p["timestamp"] or "", reverse=True)


def instaloader_posts(usernames, limit):
    import instaloader

    loader = instaloader.Instaloader(download_videos=False, save_metadata=False, max_connection_attempts=1)
    ig_user = os.getenv("IG_USERNAME")
    if ig_user:
        # Create once with: instaloader --login <IG_USERNAME>
        loader.load_session_from_file(ig_user, os.getenv("IG_SESSIONFILE") or None)
    posts = []
    for u in usernames:
        profile = instaloader.Profile.from_username(loader.context, u)
        for p in islice(profile.get_posts(), limit):
            posts.append({
                "username": u,
                "caption": p.caption or "",
                "image": p.url,
                "url": f"https://www.instagram.com/p/{p.shortcode}/",
                "timestamp": p.date_utc.isoformat(),
                "pinned": p.is_pinned,
            })
    return posts


def apify_posts(usernames, limit):
    resp = requests.post(
        APIFY_URL,
        params={"token": os.getenv("APIFY_TOKEN")},
        json={"username": usernames, "resultsLimit": limit},
        timeout=300,
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
            })
    return posts
