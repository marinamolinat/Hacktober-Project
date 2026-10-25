"""Background ingestion: scrape → POSTS → extraction → EVENTS (specs.md §4)."""
import logging
import threading

import ai
import scraper
import store

log = logging.getLogger(__name__)
_running = set()
_guard = threading.Lock()


def ingest_account(account_id, username):
    try:
        posts = scraper.scrape([username])
    except Exception as e:
        log.warning("scrape failed for %s: %s", username, e)
        store.set_ingestion_state(account_id, "retry", str(e))
        return
    outcomes = [store.upsert_post(account_id, p) for p in posts if p.get("shortcode")]
    for post in store.pending_posts(account_id):
        try:
            payload = ai.extract(post["caption"] or "", store.iso(post["posted_at"]))
            store.save_extraction(post["post_id"], post["content_hash"], payload)
        except Exception as e:
            store.save_extraction(post["post_id"], post["content_hash"], {"events": [], "warnings": []}, error=str(e)[:2000])
    created = store.sync_events(account_id)
    store.set_ingestion_state(account_id, "ok", success=True)
    log.info("ingested %s: %s, %d new events", username, {o: outcomes.count(o) for o in set(outcomes)}, created)


def queue(account_id, username):
    with _guard:
        if account_id in _running:
            return
        _running.add(account_id)

    def run():
        try:
            ingest_account(account_id, username)
        except Exception:
            log.exception("ingestion crashed for %s", username)
            store.set_ingestion_state(account_id, "retry", "internal error")
        finally:
            with _guard:
                _running.discard(account_id)

    threading.Thread(target=run, daemon=True).start()
