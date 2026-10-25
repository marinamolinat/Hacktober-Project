# InstaLetter (hackathon demo)

Enter Instagram usernames → scrape recent posts with [apify/instagram-post-scraper](https://apify.com/apify/instagram-post-scraper) → summarize + extract events with Snowflake Cortex → show a newsletter and a calendar.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: fill in Apify / Snowflake creds
python app.py          # http://localhost:5000
```

Sign up at `/signup` (email + password), follow accounts, and the newsletter/calendar fill in as each account is scraped in the background.

The data model is the 11-table schema in [`specs.md`](specs.md) §2, DDL in [`snowflake/002_schema.sql`](snowflake/002_schema.sql). With `SNOWFLAKE_ACCOUNT` blank it runs against a local SQLite copy (`local.db`); with it set, run `python manage.py init-db` once as the owner role.

With no creds it uses mock posts and a regex-based summarizer, so the UI works out of the box.

- `SCRAPER=instaloader` → real posts via [Instaloader](https://instaloader.github.io/) (free; Instagram rate-limits anonymous use, so log in a burner account once with `instaloader --login <user>` and set `IG_USERNAME`)
- `APIFY_TOKEN` set (or `SCRAPER=apify`) → real posts via Apify
- `SNOWFLAKE_*` set → data stored in `HACKATHON_DB.APP`; also set `SNOWFLAKE_EXTRACT_MODEL` for summaries/events via `AI_COMPLETE`

## Files

- `app.py` – Flask routes (`/`, `/v1/me`, `/v1/me/follows`, `/v1/newsletter`, `/v1/events`)
- `auth.py` – `/signup`, `/login`, `/logout` (passwords hashed in `USERS.PASSWORD_HASH`)
- `db.py` / `store.py` – Snowflake (or SQLite) connection and queries for the spec schema
- `ingest.py` – background scrape → `POSTS` → extraction → `EVENTS`
- `manage.py` – `init-db`, `ingest`
- `scraper.py` – Instaloader / Apify / mock backends
- `ai.py` – Cortex prompt (JSON summary + events) with heuristic fallback
- `dates.py` – tiny date parser for the fallback
- `templates/index.html` – newsletter + FullCalendar UI
