import logging
import os
import uuid
from datetime import date

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

import auth  # noqa: E402
import db  # noqa: E402
import ingest  # noqa: E402
import store  # noqa: E402

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.register_blueprint(auth.bp)
if not db.using_snowflake():
    db.init_schema()


def error(status, code, message):
    return jsonify(error={"code": code, "message": message, "request_id": str(uuid.uuid4())}), status


@app.errorhandler(db.DatabaseUnavailable)
def db_unavailable(_):
    return error(503, "dependency_unavailable", "Database unavailable.")


def int_arg(name, default, lo, hi):
    value = request.args.get(name, default, type=int)
    return value if value is not None and lo <= value <= hi else None


@app.get("/")
@auth.login_required
def index():
    return render_template("index.html", user=store.get_user(auth.current_user_id()))


@app.get("/v1/me")
@auth.login_required
def me():
    u = store.get_user(auth.current_user_id())
    return jsonify(user_id=u["user_id"], email=u["email"], display_name=u["display_name"], timezone=u["timezone"])


@app.get("/v1/me/follows")
@auth.login_required
def follows():
    return jsonify(items=store.list_follows(auth.current_user_id()))


@app.put("/v1/me/follows/<username>")
@auth.login_required
def follow(username):
    handle = store.normalize_handle(username)
    if not handle:
        return error(400, "invalid_input", "Not a valid Instagram handle.")
    account = store.get_or_create_account(handle)
    created = store.follow(auth.current_user_id(), account["account_id"])
    if account["ingestion_status"] != "ok":
        ingest.queue(account["account_id"], handle)
    return jsonify(account_id=account["account_id"], username=handle,
                   ingestion_status=account["ingestion_status"]), 201 if created else 200


@app.delete("/v1/me/follows/<account_id>")
@auth.login_required
def unfollow(account_id):
    store.unfollow(auth.current_user_id(), account_id)
    return "", 204


@app.post("/v1/me/refresh")
@auth.login_required
def refresh():
    items = store.list_follows(auth.current_user_id())
    for f in items:
        ingest.queue(f["account_id"], f["username"])
    return jsonify(queued=len(items)), 202


@app.get("/v1/newsletter")
@auth.login_required
def newsletter():
    days, limit = int_arg("days", 7, 1, 30), int_arg("limit", 20, 1, 50)
    if days is None or limit is None:
        return error(400, "invalid_input", "days must be 1-30 and limit 1-50.")
    items = store.newsletter(auth.current_user_id(), days, limit)
    return jsonify(items=items, summary=None, next_cursor=None, meta={"source_mode": "live"})


@app.get("/v1/events")
@auth.login_required
def events():
    limit = int_arg("limit", 20, 1, 50)
    try:
        dates = [date.fromisoformat(request.args[k]) if request.args.get(k) else None
                 for k in ("from_date", "through_date")]
    except ValueError:
        dates = None
    if limit is None or dates is None:
        return error(400, "invalid_input", "limit must be 1-50; dates must be YYYY-MM-DD.")
    items = store.events_feed(auth.current_user_id(), limit, *dates)
    return jsonify(items=items, next_cursor=None, meta={"search_degraded": True, "source_mode": "live", "warnings": []})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
