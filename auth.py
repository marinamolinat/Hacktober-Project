import re
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import store

bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def current_user_id():
    return session.get("user_id")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id() or not store.get_user(current_user_id()):
            session.clear()
            if request.path.startswith("/v1/"):
                return jsonify(error={"code": "unauthenticated", "message": "Log in first."}), 401
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not EMAIL_RE.match(email):
            flash("Enter a valid email.")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.")
        else:
            user_id = store.create_user(email, generate_password_hash(password))
            if user_id:
                session.clear()
                session["user_id"] = user_id
                return redirect(url_for("index"))
            flash("An account with that email already exists.")
    return render_template("auth.html", mode="signup")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = store.get_user_by_email(request.form.get("email", "").strip().lower())
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["user_id"]
            return redirect(url_for("index"))
        flash("Wrong email or password.")
    return render_template("auth.html", mode="login")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
