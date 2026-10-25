import os
import random
from datetime import datetime, timedelta, timezone

import requests

APIFY_URL = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items"


def scrape(usernames, limit=5):
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return mock_posts(usernames, limit)
    resp = requests.post(
        APIFY_URL,
        params={"token": token},
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
