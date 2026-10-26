# this is the web server for the shop
# run it with python backend/app.py then go to http://127.0.0.1:5000
# the frontend hits these /api urls and gets json back
# all the sql lives in db.py so this file just checks input and replies

import os                                          # lets us read environment variables
from functools import wraps                        # helper for making our own decorators
from flask import Flask, jsonify, request, session # flask pieces we need
import db                                          # our db.py file

app = Flask(__name__)                                                  # make the flask app
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")   # signs the login cookie, use a real random one when we go live
app.teardown_appcontext(db.close_db)                                   # close the db after every request


# turns a db row into a normal dict so jsonify can send it
def to_dict(row):
    return dict(row) if row is not None else None


# same as to_dict but also adds price in dollars for the frontend
def public_listing(row):
    listing = to_dict(row)                             # row to dict
    listing["price"] = listing["price_cents"] / 100    # 4500 cents becomes 45.0
    return listing


# put @login_required on a route and it blocks people who arent logged in
def login_required(view):
    @wraps(view)                                         # keeps the route's real name so flask doesnt get confused
    def wrapper(*args, **kwargs):
        if "user_id" not in session:                     # no user in the cookie
            return jsonify(error="Login required"), 401  # 401 means not logged in
        return view(*args, **kwargs)                     # logged in so run the real route
    return wrapper


# auth

# sign up
@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}                         # read the json body, empty dict if there isnt one
    required = ["email", "password", "first_name", "last_name"]        # fields we need
    if not all(data.get(f) for f in required):                         # any of them missing or blank
        return jsonify(error=f"Required fields: {', '.join(required)}"), 400   # 400 means bad request
    if len(data["password"]) < 8:                                      # password too short
        return jsonify(error="Password must be at least 8 characters"), 400

    try:
        user_id = db.create_user(db.get_db(), data["email"], data["password"],   # try making the account
                                 data["first_name"], data["last_name"])
    except ValueError as e:                                            # bad domain or email taken
        return jsonify(error=str(e)), 400

    session["user_id"] = user_id                                       # log them in right away
    return jsonify(user=to_dict(db.get_user(db.get_db(), user_id))), 201   # 201 means created


# log in
@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}                                          # read the body
    user = db.authenticate(db.get_db(), data.get("email", ""), data.get("password", ""))  # check email and password
    if user is None:                                                                    # didnt match
        return jsonify(error="Wrong email or password"), 401
    session["user_id"] = user["id"]                                                     # save who they are in the cookie
    return jsonify(user=to_dict(db.get_user(db.get_db(), user["id"])))                  # send back their info


# log out
@app.post("/api/logout")
def logout():
    session.clear()            # wipe the cookie
    return jsonify(ok=True)


# who am i
@app.get("/api/me")
@login_required
def me():
    return jsonify(user=to_dict(db.get_user(db.get_db(), session["user_id"])))   # send back the logged in user


# categories and listings

# all categories
@app.get("/api/categories")
def categories():
    return jsonify([to_dict(c) for c in db.get_categories(db.get_db())])   # turn each row into a dict


# browse and search, like /api/listings?q=desk&category=3
@app.get("/api/listings")
def listings():
    rows = db.search_listings(
        db.get_db(),
        query=request.args.get("q"),                           # the ?q= part
        category_id=request.args.get("category", type=int),    # the ?category= part as a number
    )
    return jsonify([public_listing(r) for r in rows])


# one listing with all its pics
@app.get("/api/listings/<int:listing_id>")
def listing_detail(listing_id):
    conn = db.get_db()
    row = db.get_listing(conn, listing_id)                     # look it up
    if row is None or row["status"] == "removed":              # doesnt exist or got taken down
        return jsonify(error="Listing not found"), 404         # 404 means not found
    listing = public_listing(row)
    listing["images"] = [i["image_path"] for i in db.get_listing_images(conn, listing_id)]   # add the pic list
    return jsonify(listing)


# post a new listing
@app.post("/api/listings")
@login_required
def new_listing():
    data = request.get_json(silent=True) or {}
    try:
        price_cents = round(float(data["price"]) * 100)        # 12.50 becomes 1250
        listing_id = db.create_listing(
            db.get_db(),
            seller_id=session["user_id"],                      # seller is whoever is logged in
            category_id=int(data["category_id"]),
            title=data["title"],
            price_cents=price_cents,
            description=data.get("description", ""),          # optional
            condition=data.get("condition", "used"),          # optional, used if missing
            image_paths=data.get("images", []),                # optional list of pic paths
        )
    except (KeyError, ValueError, TypeError):                  # missing field or not a number
        return jsonify(error="Need title, price and category_id"), 400
    except db.sqlite3.IntegrityError as e:                     # broke a db rule like a bad condition word
        return jsonify(error=f"Invalid listing: {e}"), 400
    return jsonify(id=listing_id), 201


# mark a listing active, sold or removed
@app.post("/api/listings/<int:listing_id>/status")
@login_required
def update_listing_status(listing_id):
    status = (request.get_json(silent=True) or {}).get("status")       # read the new status
    if status not in ("active", "sold", "removed"):                    # only these are allowed
        return jsonify(error="status must be active, sold or removed"), 400
    if not db.set_listing_status(db.get_db(), listing_id, session["user_id"], status):   # nothing changed
        return jsonify(error="Not your listing"), 403                  # 403 means not allowed
    return jsonify(ok=True)


# everything one user is selling
@app.get("/api/users/<int:user_id>/listings")
def user_listings(user_id):
    return jsonify([public_listing(r) for r in db.get_listings_by_seller(db.get_db(), user_id)])


# favorites

# my saved listings
@app.get("/api/favorites")
@login_required
def favorites():
    return jsonify([public_listing(r) for r in db.get_favorites(db.get_db(), session["user_id"])])


# save a listing
@app.post("/api/favorites/<int:listing_id>")
@login_required
def add_favorite(listing_id):
    try:
        db.add_favorite(db.get_db(), session["user_id"], listing_id)
    except db.sqlite3.IntegrityError:                          # foreign key failed so the listing doesnt exist
        return jsonify(error="Listing not found"), 404
    return jsonify(ok=True)


# unsave a listing
@app.delete("/api/favorites/<int:listing_id>")
@login_required
def remove_favorite(listing_id):
    db.remove_favorite(db.get_db(), session["user_id"], listing_id)
    return jsonify(ok=True)


# messaging

# all my chats
@app.get("/api/conversations")
@login_required
def conversations():
    return jsonify([to_dict(c) for c in db.get_conversations_for_user(db.get_db(), session["user_id"])])


# buyer messages the seller about a listing, starts a chat if there isnt one
@app.post("/api/listings/<int:listing_id>/messages")
@login_required
def message_seller(listing_id):
    conn = db.get_db()
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()   # the message text, blank if missing
    listing = db.get_listing(conn, listing_id)                 # find the listing
    if listing is None:                                        # doesnt exist
        return jsonify(error="Listing not found"), 404
    if listing["seller_id"] == session["user_id"]:             # seller trying to message themself
        return jsonify(error="You can't message yourself"), 400
    if not body:                                               # empty message
        return jsonify(error="Message can't be empty"), 400

    convo_id = db.get_or_create_conversation(conn, listing_id, session["user_id"])   # find or start the chat
    db.send_message(conn, convo_id, session["user_id"], body)                        # send it
    return jsonify(conversation_id=convo_id), 201


# read a chat
@app.get("/api/conversations/<int:convo_id>/messages")
@login_required
def conversation_messages(convo_id):
    conn = db.get_db()
    if not db.is_conversation_participant(conn, convo_id, session["user_id"]):   # not the buyer or seller
        return jsonify(error="Not your conversation"), 403
    return jsonify([to_dict(m) for m in db.get_messages(conn, convo_id)])


# reply in a chat
@app.post("/api/conversations/<int:convo_id>/messages")
@login_required
def reply(convo_id):
    conn = db.get_db()
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()   # the message text
    if not db.is_conversation_participant(conn, convo_id, session["user_id"]):   # not in this chat
        return jsonify(error="Not your conversation"), 403
    if not body:                                                               # empty message
        return jsonify(error="Message can't be empty"), 400
    return jsonify(id=db.send_message(conn, convo_id, session["user_id"], body)), 201


if __name__ == "__main__":                                     # only when you run this file directly
    if not db.DB_PATH.exists():                                # no db file yet
        print("No database yet, run: python backend/database/init_db.py")
    app.run(debug=True)                                        # start the server, debug reloads when you save
