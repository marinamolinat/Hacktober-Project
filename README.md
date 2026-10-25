# InstaLetter (hackathon demo)

Enter Instagram usernames → scrape recent posts with [apify/instagram-post-scraper](https://apify.com/apify/instagram-post-scraper) → summarize + extract events with Snowflake Cortex → show a newsletter and a calendar.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: fill in Apify / Snowflake creds
python app.py          # http://localhost:5000
```

With no creds it uses mock posts and a regex-based summarizer, so the UI works out of the box.

- `APIFY_TOKEN` set → real Instagram posts
- `SNOWFLAKE_*` set → summaries/events via `SNOWFLAKE.CORTEX.COMPLETE`

## Files

- `app.py` – Flask routes (`/`, `POST /api/newsletter`)
- `scraper.py` – Apify call + mock data
- `ai.py` – Cortex prompt (JSON summary + event) with heuristic fallback
- `dates.py` – tiny date parser for the fallback
- `templates/index.html` – newsletter + FullCalendar UI
