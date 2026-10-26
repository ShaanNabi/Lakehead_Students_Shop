# this file is the only place that talks to the database
# the rest of the app just calls these functions instead of writing sql
# uses python's built in sqlite3 so no extra installs

import hashlib            # for scrambling passwords
import hmac               # for safely comparing password hashes
import os                 # for making random bytes (the salt)
import sqlite3            # the sqlite library
from pathlib import Path  # makes file paths work on any computer
from flask import g       # flask's per request storage box


DB_PATH = Path(__file__).resolve().parent / "lakehead_shop.db"   # db file sits next to this file

PASSWORD_ITERATIONS = 600_000   # how many times we scramble a password, more is slower to crack


# connection stuff

# opens a connection to the db, routes should use get_db instead
def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)              # open the db file
    conn.row_factory = sqlite3.Row               # lets us do row["title"] instead of row[3]
    conn.execute("PRAGMA foreign_keys = ON")     # sqlite has these off by default so turn them on
    return conn                                  # hand back the connection


# gives each web request its own connection and reuses it
def get_db():
    if "db" not in g:          # first time this request asks for the db
        g.db = connect()       # open one and stash it
    return g.db                # give back the stashed one


# closes the connection when the request is done
def close_db(exception=None):
    db = g.pop("db", None)     # take the connection out if there is one
    if db is not None:         # only close it if it was opened
        db.close()             # close it


# password stuff
# saved passwords look like pbkdf2_sha256$iterations$salt$hash

# turns a plain password into a scrambled one we can save
def hash_password(password):
    salt = os.urandom(16)                                                                 # 16 random bytes so same passwords dont look the same
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)  # scramble it a bunch of times
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"            # glue it all into one string


# checks if a typed password matches the saved one
def check_password(password, stored):
    _, iterations, salt_hex, hash_hex = stored.split("$")      # split the saved string back into parts
    digest = hashlib.pbkdf2_hmac(                              # scramble the typed password the same way
        "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(digest.hex(), hash_hex)         # compare them safely, true if they match


# users

# finds which school an email belongs to, none if no match
def find_university_for_email(db, email):
    domain = email.rsplit("@", 1)[-1].lower()                       # grab everything after the @
    return db.execute(
        "SELECT * FROM universities WHERE email_domain = ?", (domain,)   # ? gets filled with domain safely
    ).fetchone()                                                    # one row or none


# makes a new account, throws ValueError if the email isnt allowed or is taken
def create_user(db, email, password, first_name, last_name):
    university = find_university_for_email(db, email)                         # check their school
    if university is None:                                                    # not a school we know
        raise ValueError("Only university emails (e.g. @lakeheadu.ca) can sign up")

    try:
        cur = db.execute(                                                     # add the user row
            """INSERT INTO users (university_id, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (university["id"], email.strip().lower(), hash_password(password), # each value fills a ? in order
             first_name.strip(), last_name.strip()),                          # strip removes extra spaces
        )
        db.commit()                                                           # save it
    except sqlite3.IntegrityError:                                            # unique email rule got broken
        raise ValueError("An account with that email already exists")
    return cur.lastrowid                                                      # the new user's id


# finds a user by email, includes the password hash
def get_user_by_email(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()


# finds a user by id, leaves out the password hash so we can send it to the browser
def get_user(db, user_id):
    return db.execute(
        """SELECT id, university_id, email, first_name, last_name, bio, created_at
           FROM users WHERE id = ?""",
        (user_id,),            # the comma makes it a tuple, sqlite needs that
    ).fetchone()


# login check, gives back the user if email and password are right
def authenticate(db, email, password):
    user = get_user_by_email(db, email)                           # look them up
    if user and check_password(password, user["password_hash"]):  # they exist and password matches
        return user                                               # logged in
    return None                                                   # wrong email or password


# categories

# all categories sorted a to z
def get_categories(db):
    return db.execute("SELECT * FROM categories ORDER BY name").fetchall()


# listings

# shared select so every listing query gives back the same columns
LISTING_SELECT = """
    SELECT l.*,                                          -- every listing column
           u.first_name || ' ' || u.last_name AS seller_name, -- glue first and last name together
           c.name AS category_name,                      -- the category's name
           (SELECT image_path FROM listing_images i      -- grab one pic
             WHERE i.listing_id = l.id                   -- for this listing
             ORDER BY i.sort_order LIMIT 1) AS cover_image -- the first one
    FROM listings l                                      -- l is a nickname for listings
    JOIN users u      ON u.id = l.seller_id              -- hook up the seller
    JOIN categories c ON c.id = l.category_id            -- hook up the category
"""


# active listings newest first, can filter by search words and category
def search_listings(db, query=None, category_id=None, limit=50):
    sql = LISTING_SELECT + " WHERE l.status = 'active'"   # only stuff still for sale
    params = []                                            # values for the ? spots

    if query:                                                         # they typed a search
        sql += " AND (l.title LIKE ? OR l.description LIKE ?)"        # look in title or description
        like = f"%{query}%"                                           # % means anything before or after
        params += [like, like]                                        # once for title once for description

    if category_id:                                       # they picked a category
        sql += " AND l.category_id = ?"                   # only that category
        params.append(category_id)                        # add it to the values

    sql += " ORDER BY l.created_at DESC, l.id DESC LIMIT ?"   # newest first, cap how many
    params.append(limit)                                      # the cap
    return db.execute(sql, params).fetchall()                 # run it and get all rows


# one listing by id
def get_listing(db, listing_id):
    return db.execute(LISTING_SELECT + " WHERE l.id = ?", (listing_id,)).fetchone()


# all pics for one listing in order
def get_listing_images(db, listing_id):
    return db.execute(
        "SELECT image_path FROM listing_images WHERE listing_id = ? ORDER BY sort_order",
        (listing_id,),
    ).fetchall()


# everything one user is selling, skips removed ones
def get_listings_by_seller(db, seller_id):
    return db.execute(
        LISTING_SELECT + " WHERE l.seller_id = ? AND l.status != 'removed' ORDER BY l.created_at DESC",
        (seller_id,),
    ).fetchall()


# posts a new listing plus its pics, gives back the new id
def create_listing(db, seller_id, category_id, title, price_cents,
                   description="", condition="used", image_paths=()):
    cur = db.execute(                                                          # add the listing row
        """INSERT INTO listings (seller_id, category_id, title, description, price_cents, condition)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (seller_id, category_id, title.strip(), description.strip(), price_cents, condition),
    )
    listing_id = cur.lastrowid                                                 # id of the row we just made
    db.executemany(                                                            # add every pic in one go
        "INSERT INTO listing_images (listing_id, image_path, sort_order) VALUES (?, ?, ?)",
        [(listing_id, path, i) for i, path in enumerate(image_paths)],         # enumerate gives 0, 1, 2 for sort order
    )
    db.commit()                                                                # save both
    return listing_id


# sets a listing to active, sold or removed, only works if you're the seller
def set_listing_status(db, listing_id, seller_id, status):
    cur = db.execute(
        "UPDATE listings SET status = ? WHERE id = ? AND seller_id = ?",   # seller check is right in the where
        (status, listing_id, seller_id),
    )
    db.commit()                    # save it
    return cur.rowcount == 1       # true if a row changed, false if not yours


# favorites

# saves a listing, does nothing if it's already saved
def add_favorite(db, user_id, listing_id):
    db.execute(
        "INSERT OR IGNORE INTO favorites (user_id, listing_id) VALUES (?, ?)",   # or ignore skips duplicates
        (user_id, listing_id),
    )
    db.commit()


# unsaves a listing
def remove_favorite(db, user_id, listing_id):
    db.execute(
        "DELETE FROM favorites WHERE user_id = ? AND listing_id = ?",
        (user_id, listing_id),
    )
    db.commit()


# all listings a user saved, newest save first
def get_favorites(db, user_id):
    return db.execute(
        LISTING_SELECT + """ JOIN favorites f ON f.listing_id = l.id
                             WHERE f.user_id = ? ORDER BY f.created_at DESC""",
        (user_id,),
    ).fetchall()


# messaging

# finds the chat for this buyer and listing or makes one, gives back its id
def get_or_create_conversation(db, listing_id, buyer_id):
    db.execute(
        "INSERT OR IGNORE INTO conversations (listing_id, buyer_id) VALUES (?, ?)",  # makes it only if it doesnt exist
        (listing_id, buyer_id),
    )
    db.commit()
    return db.execute(
        "SELECT id FROM conversations WHERE listing_id = ? AND buyer_id = ?",        # now grab its id
        (listing_id, buyer_id),
    ).fetchone()["id"]


# adds a message to a chat, gives back the message id
def send_message(db, conversation_id, sender_id, body):
    cur = db.execute(
        "INSERT INTO messages (conversation_id, sender_id, body) VALUES (?, ?, ?)",
        (conversation_id, sender_id, body.strip()),
    )
    db.commit()
    return cur.lastrowid


# every message in a chat, oldest first
def get_messages(db, conversation_id):
    return db.execute(
        """SELECT m.*, u.first_name AS sender_name   -- message plus who sent it
           FROM messages m JOIN users u ON u.id = m.sender_id
           WHERE m.conversation_id = ?
           ORDER BY m.sent_at, m.id""",
        (conversation_id,),
    ).fetchall()


# true if the user is the buyer or the seller in this chat
def is_conversation_participant(db, conversation_id, user_id):
    row = db.execute(
        """SELECT 1 FROM conversations c JOIN listings l ON l.id = c.listing_id
           WHERE c.id = ? AND (c.buyer_id = ? OR l.seller_id = ?)""",   # buyer or seller counts
        (conversation_id, user_id, user_id),
    ).fetchone()
    return row is not None       # found a row means they're in it


# every chat a user is in, as buyer or seller
def get_conversations_for_user(db, user_id):
    return db.execute(
        """SELECT c.id, c.listing_id, l.title AS listing_title, c.buyer_id, l.seller_id,
                  (SELECT body FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.sent_at DESC, m.id DESC LIMIT 1) AS last_message -- newest message for the preview
           FROM conversations c
           JOIN listings l ON l.id = c.listing_id
           WHERE c.buyer_id = ? OR l.seller_id = ?
           ORDER BY c.created_at DESC""",
        (user_id, user_id),
    ).fetchall()
