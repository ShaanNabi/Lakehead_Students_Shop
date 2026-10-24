"""
Lakehead Students Shop - Flask backend (JSON API).

    python backend/app.py      -> http://127.0.0.1:5000

The frontend calls these /api/... routes with fetch(). All database work
lives in db.py, so routes just validate input and return JSON.
"""

import os
from functools import wraps

from flask import Flask, jsonify, request, session

import db

app = Flask(__name__)
# Signs the login cookie. Set a real random value in production.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.teardown_appcontext(db.close_db)


def to_dict(row):
    return dict(row) if row is not None else None


def public_listing(row):
    listing = to_dict(row)
    listing["price"] = listing["price_cents"] / 100
    return listing


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="Login required"), 401
        return view(*args, **kwargs)
    return wrapper


# -------------------------------------------------------------
# Auth
# -------------------------------------------------------------

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    required = ["email", "password", "first_name", "last_name"]
    if not all(data.get(f) for f in required):
        return jsonify(error=f"Required fields: {', '.join(required)}"), 400
    if len(data["password"]) < 8:
        return jsonify(error="Password must be at least 8 characters"), 400

    try:
        user_id = db.create_user(db.get_db(), data["email"], data["password"],
                                 data["first_name"], data["last_name"])
    except ValueError as e:
        return jsonify(error=str(e)), 400

    session["user_id"] = user_id
    return jsonify(user=to_dict(db.get_user(db.get_db(), user_id))), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    user = db.authenticate(db.get_db(), data.get("email", ""), data.get("password", ""))
    if user is None:
        return jsonify(error="Wrong email or password"), 401
    session["user_id"] = user["id"]
    return jsonify(user=to_dict(db.get_user(db.get_db(), user["id"])))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
@login_required
def me():
    return jsonify(user=to_dict(db.get_user(db.get_db(), session["user_id"])))


# -------------------------------------------------------------
# Categories + listings
# -------------------------------------------------------------

@app.get("/api/categories")
def categories():
    return jsonify([to_dict(c) for c in db.get_categories(db.get_db())])


@app.get("/api/listings")
def listings():
    rows = db.search_listings(
        db.get_db(),
        query=request.args.get("q"),
        category_id=request.args.get("category", type=int),
    )
    return jsonify([public_listing(r) for r in rows])


@app.get("/api/listings/<int:listing_id>")
def listing_detail(listing_id):
    conn = db.get_db()
    row = db.get_listing(conn, listing_id)
    if row is None or row["status"] == "removed":
        return jsonify(error="Listing not found"), 404
    listing = public_listing(row)
    listing["images"] = [i["image_path"] for i in db.get_listing_images(conn, listing_id)]
    return jsonify(listing)


@app.post("/api/listings")
@login_required
def new_listing():
    data = request.get_json(silent=True) or {}
    try:
        price_cents = round(float(data["price"]) * 100)
        listing_id = db.create_listing(
            db.get_db(),
            seller_id=session["user_id"],
            category_id=int(data["category_id"]),
            title=data["title"],
            price_cents=price_cents,
            description=data.get("description", ""),
            condition=data.get("condition", "used"),
            image_paths=data.get("images", []),
        )
    except (KeyError, ValueError, TypeError):
        return jsonify(error="Need title, price and category_id"), 400
    except db.sqlite3.IntegrityError as e:
        return jsonify(error=f"Invalid listing: {e}"), 400
    return jsonify(id=listing_id), 201


@app.post("/api/listings/<int:listing_id>/status")
@login_required
def update_listing_status(listing_id):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ("active", "sold", "removed"):
        return jsonify(error="status must be active, sold or removed"), 400
    if not db.set_listing_status(db.get_db(), listing_id, session["user_id"], status):
        return jsonify(error="Not your listing"), 403
    return jsonify(ok=True)


@app.get("/api/users/<int:user_id>/listings")
def user_listings(user_id):
    return jsonify([public_listing(r) for r in db.get_listings_by_seller(db.get_db(), user_id)])


# -------------------------------------------------------------
# Favorites
# -------------------------------------------------------------

@app.get("/api/favorites")
@login_required
def favorites():
    return jsonify([public_listing(r) for r in db.get_favorites(db.get_db(), session["user_id"])])


@app.post("/api/favorites/<int:listing_id>")
@login_required
def add_favorite(listing_id):
    try:
        db.add_favorite(db.get_db(), session["user_id"], listing_id)
    except db.sqlite3.IntegrityError:
        return jsonify(error="Listing not found"), 404
    return jsonify(ok=True)


@app.delete("/api/favorites/<int:listing_id>")
@login_required
def remove_favorite(listing_id):
    db.remove_favorite(db.get_db(), session["user_id"], listing_id)
    return jsonify(ok=True)


# -------------------------------------------------------------
# Messaging
# -------------------------------------------------------------

@app.get("/api/conversations")
@login_required
def conversations():
    return jsonify([to_dict(c) for c in db.get_conversations_for_user(db.get_db(), session["user_id"])])


@app.post("/api/listings/<int:listing_id>/messages")
@login_required
def message_seller(listing_id):
    """Buyer starts (or continues) a chat about a listing."""
    conn = db.get_db()
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    listing = db.get_listing(conn, listing_id)
    if listing is None:
        return jsonify(error="Listing not found"), 404
    if listing["seller_id"] == session["user_id"]:
        return jsonify(error="You can't message yourself"), 400
    if not body:
        return jsonify(error="Message can't be empty"), 400

    convo_id = db.get_or_create_conversation(conn, listing_id, session["user_id"])
    db.send_message(conn, convo_id, session["user_id"], body)
    return jsonify(conversation_id=convo_id), 201


@app.get("/api/conversations/<int:convo_id>/messages")
@login_required
def conversation_messages(convo_id):
    conn = db.get_db()
    if not db.is_conversation_participant(conn, convo_id, session["user_id"]):
        return jsonify(error="Not your conversation"), 403
    return jsonify([to_dict(m) for m in db.get_messages(conn, convo_id)])


@app.post("/api/conversations/<int:convo_id>/messages")
@login_required
def reply(convo_id):
    conn = db.get_db()
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    if not db.is_conversation_participant(conn, convo_id, session["user_id"]):
        return jsonify(error="Not your conversation"), 403
    if not body:
        return jsonify(error="Message can't be empty"), 400
    return jsonify(id=db.send_message(conn, convo_id, session["user_id"], body)), 201


if __name__ == "__main__":
    if not db.DB_PATH.exists():
        print("No database yet, run: python backend/database/init_db.py")
    app.run(debug=True)
