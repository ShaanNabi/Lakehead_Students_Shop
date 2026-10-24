"""
Database helper for Lakehead Students Shop.

Everything that touches SQLite goes through this file, so the rest of the
app never writes raw SQL. Uses Python's built-in sqlite3 module (no ORM),
so what you see here is exactly what runs against the database.
"""

import hashlib
import hmac
import os
import sqlite3
from pathlib import Path

from flask import g

DB_PATH = Path(__file__).resolve().parent / "lakehead_shop.db"

PASSWORD_ITERATIONS = 600_000


# -------------------------------------------------------------
# Connection
# -------------------------------------------------------------

def connect(db_path=DB_PATH):
    """Open a raw connection. Use get_db() inside Flask routes instead."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row             # rows act like dicts: row["title"]
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite has these OFF by default
    return conn


def get_db():
    """One connection per web request, stored on Flask's `g` object."""
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# -------------------------------------------------------------
# Passwords (PBKDF2 from the standard library)
# Stored format: pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>
# -------------------------------------------------------------

def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def check_password(password, stored):
    _, iterations, salt_hex, hash_hex = stored.split("$")
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(digest.hex(), hash_hex)


# -------------------------------------------------------------
# Users
# -------------------------------------------------------------

def find_university_for_email(db, email):
    """Return the university row whose domain matches the email, or None."""
    domain = email.rsplit("@", 1)[-1].lower()
    return db.execute(
        "SELECT * FROM universities WHERE email_domain = ?", (domain,)
    ).fetchone()


def create_user(db, email, password, first_name, last_name):
    """Insert a new user. Raises ValueError if the email domain isn't allowed
    or the email is already taken."""
    university = find_university_for_email(db, email)
    if university is None:
        raise ValueError("Only university emails (e.g. @lakeheadu.ca) can sign up")

    try:
        cur = db.execute(
            """INSERT INTO users (university_id, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (university["id"], email.strip().lower(), hash_password(password),
             first_name.strip(), last_name.strip()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise ValueError("An account with that email already exists")
    return cur.lastrowid


def get_user_by_email(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()


def get_user(db, user_id):
    return db.execute(
        """SELECT id, university_id, email, first_name, last_name, bio, created_at
           FROM users WHERE id = ?""",
        (user_id,),
    ).fetchone()


def authenticate(db, email, password):
    """Return the user row if email + password are correct, else None."""
    user = get_user_by_email(db, email)
    if user and check_password(password, user["password_hash"]):
        return user
    return None


# -------------------------------------------------------------
# Categories
# -------------------------------------------------------------

def get_categories(db):
    return db.execute("SELECT * FROM categories ORDER BY name").fetchall()


# -------------------------------------------------------------
# Listings
# -------------------------------------------------------------

# Shared SELECT so every listing query returns the same shape:
# listing columns + seller name + category name + first image
LISTING_SELECT = """
    SELECT l.*,
           u.first_name || ' ' || u.last_name AS seller_name,
           c.name AS category_name,
           (SELECT image_path FROM listing_images i
             WHERE i.listing_id = l.id
             ORDER BY i.sort_order LIMIT 1) AS cover_image
    FROM listings l
    JOIN users u      ON u.id = l.seller_id
    JOIN categories c ON c.id = l.category_id
"""


def search_listings(db, query=None, category_id=None, limit=50):
    """Active listings, newest first, optionally filtered by text and category."""
    sql = LISTING_SELECT + " WHERE l.status = 'active'"
    params = []

    if query:
        sql += " AND (l.title LIKE ? OR l.description LIKE ?)"
        like = f"%{query}%"
        params += [like, like]

    if category_id:
        sql += " AND l.category_id = ?"
        params.append(category_id)

    sql += " ORDER BY l.created_at DESC, l.id DESC LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()


def get_listing(db, listing_id):
    return db.execute(LISTING_SELECT + " WHERE l.id = ?", (listing_id,)).fetchone()


def get_listing_images(db, listing_id):
    return db.execute(
        "SELECT image_path FROM listing_images WHERE listing_id = ? ORDER BY sort_order",
        (listing_id,),
    ).fetchall()


def get_listings_by_seller(db, seller_id):
    return db.execute(
        LISTING_SELECT + " WHERE l.seller_id = ? AND l.status != 'removed' ORDER BY l.created_at DESC",
        (seller_id,),
    ).fetchall()


def create_listing(db, seller_id, category_id, title, price_cents,
                   description="", condition="used", image_paths=()):
    cur = db.execute(
        """INSERT INTO listings (seller_id, category_id, title, description, price_cents, condition)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (seller_id, category_id, title.strip(), description.strip(), price_cents, condition),
    )
    listing_id = cur.lastrowid
    db.executemany(
        "INSERT INTO listing_images (listing_id, image_path, sort_order) VALUES (?, ?, ?)",
        [(listing_id, path, i) for i, path in enumerate(image_paths)],
    )
    db.commit()
    return listing_id


def set_listing_status(db, listing_id, seller_id, status):
    """Mark a listing 'active', 'sold' or 'removed'. Only the seller can do this.
    Returns True if a row was updated."""
    cur = db.execute(
        "UPDATE listings SET status = ? WHERE id = ? AND seller_id = ?",
        (status, listing_id, seller_id),
    )
    db.commit()
    return cur.rowcount == 1


# -------------------------------------------------------------
# Favorites
# -------------------------------------------------------------

def add_favorite(db, user_id, listing_id):
    db.execute(
        "INSERT OR IGNORE INTO favorites (user_id, listing_id) VALUES (?, ?)",
        (user_id, listing_id),
    )
    db.commit()


def remove_favorite(db, user_id, listing_id):
    db.execute(
        "DELETE FROM favorites WHERE user_id = ? AND listing_id = ?",
        (user_id, listing_id),
    )
    db.commit()


def get_favorites(db, user_id):
    return db.execute(
        LISTING_SELECT + """ JOIN favorites f ON f.listing_id = l.id
                             WHERE f.user_id = ? ORDER BY f.created_at DESC""",
        (user_id,),
    ).fetchall()


# -------------------------------------------------------------
# Messaging
# -------------------------------------------------------------

def get_or_create_conversation(db, listing_id, buyer_id):
    db.execute(
        "INSERT OR IGNORE INTO conversations (listing_id, buyer_id) VALUES (?, ?)",
        (listing_id, buyer_id),
    )
    db.commit()
    return db.execute(
        "SELECT id FROM conversations WHERE listing_id = ? AND buyer_id = ?",
        (listing_id, buyer_id),
    ).fetchone()["id"]


def send_message(db, conversation_id, sender_id, body):
    cur = db.execute(
        "INSERT INTO messages (conversation_id, sender_id, body) VALUES (?, ?, ?)",
        (conversation_id, sender_id, body.strip()),
    )
    db.commit()
    return cur.lastrowid


def get_messages(db, conversation_id):
    return db.execute(
        """SELECT m.*, u.first_name AS sender_name
           FROM messages m JOIN users u ON u.id = m.sender_id
           WHERE m.conversation_id = ?
           ORDER BY m.sent_at, m.id""",
        (conversation_id,),
    ).fetchall()


def is_conversation_participant(db, conversation_id, user_id):
    """True if the user is the buyer or the seller in this conversation."""
    row = db.execute(
        """SELECT 1 FROM conversations c JOIN listings l ON l.id = c.listing_id
           WHERE c.id = ? AND (c.buyer_id = ? OR l.seller_id = ?)""",
        (conversation_id, user_id, user_id),
    ).fetchone()
    return row is not None


def get_conversations_for_user(db, user_id):
    """Every conversation the user is in, as buyer or as seller."""
    return db.execute(
        """SELECT c.id, c.listing_id, l.title AS listing_title, c.buyer_id, l.seller_id,
                  (SELECT body FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.sent_at DESC, m.id DESC LIMIT 1) AS last_message
           FROM conversations c
           JOIN listings l ON l.id = c.listing_id
           WHERE c.buyer_id = ? OR l.seller_id = ?
           ORDER BY c.created_at DESC""",
        (user_id, user_id),
    ).fetchall()
