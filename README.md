# InstaLetter (hackathon demo)

Enter Instagram usernames → scrape recent posts with [apify/instagram-post-scraper](https://apify.com/apify/instagram-post-scraper) → summarize + extract events with Snowflake Cortex → show a newsletter and a calendar.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: fill in Apify / Snowflake creds
python app.py          # http://localhost:5000
```

With no creds it uses mock posts and a regex-based summarizer, so the UI works out of the box.

- `SCRAPER=instaloader` → real posts via [Instaloader](https://instaloader.github.io/) (free; Instagram rate-limits anonymous use, so log in a burner account once with `instaloader --login <user>` and set `IG_USERNAME`)
- `APIFY_TOKEN` set (or `SCRAPER=apify`) → real posts via Apify
- `SNOWFLAKE_*` set → summaries/events via `SNOWFLAKE.CORTEX.COMPLETE`

## Files

- `app.py` – Flask routes (`/`, `POST /api/newsletter`)
- `scraper.py` – Instaloader / Apify / mock backends
- `ai.py` – Cortex prompt (JSON summary + event) with heuristic fallback
- `dates.py` – tiny date parser for the fallback
- `templates/index.html` – newsletter + FullCalendar UI
