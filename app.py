from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import ai
import scraper

load_dotenv()
app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/newsletter")
def newsletter():
    raw = request.json.get("usernames", "")
    usernames = [u.strip().lstrip("@") for u in raw.replace("\n", ",").split(",") if u.strip()]
    if not usernames:
        return jsonify(error="Enter at least one username"), 400
    posts = ai.analyze(scraper.scrape(usernames))
    events = [
        {**p["event"], "username": p["username"], "url": p["url"]}
        for p in posts if p.get("event")
    ]
    return jsonify(posts=posts, events=events)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
