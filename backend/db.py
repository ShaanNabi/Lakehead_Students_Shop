import hashlib
import hmac
import os

import psycopg
from psycopg.rows import dict_row
from flask import g

PASSWORD_ITERATIONS = 600_000


# connection stuff

def connect():
    database_url = os.environ.get("SUPABASE_DB_URL")

    if not database_url:
        raise RuntimeError("SUPABASE_DB_URL is missing. Run  python run.py  once and it sets up your .env file.")

    return psycopg.connect(
        database_url,
        sslmode="require",
        row_factory=dict_row
    )


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


# password stuff

def hash_password(password):
    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PASSWORD_ITERATIONS
    )

    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def check_password(password, stored):
    _, iterations, salt_hex, hash_hex = stored.split("$")

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt_hex),
        int(iterations)
    )

    return hmac.compare_digest(digest.hex(), hash_hex)


# users

def find_university_for_email(db, email):
    domain = email.rsplit("@", 1)[-1].lower()

    return db.execute(
        "SELECT * FROM universities WHERE email_domain = %s",
        (domain,)
    ).fetchone()


def create_user(db, email, password, first_name, last_name):
    university = find_university_for_email(db, email)

    if university is None:
        raise ValueError("Only university emails (e.g. @lakeheadu.ca) can sign up")

    try:
        cur = db.execute(
            """
            INSERT INTO users (
                university_id, email, password_hash, first_name, last_name
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                university["id"],
                email.strip().lower(),
                hash_password(password),
                first_name.strip(),
                last_name.strip()
            )
        )

        db.commit()
        return cur.fetchone()["id"]

    except psycopg.IntegrityError:
        db.rollback()
        raise ValueError("An account with that email already exists")


def get_user_by_email(db, email):
    return db.execute(
        "SELECT * FROM users WHERE email = %s",
        (email.strip().lower(),)
    ).fetchone()


def get_user(db, user_id):
    return db.execute(
        """
        SELECT id, university_id, email, first_name, last_name, bio, created_at
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    ).fetchone()


def authenticate(db, email, password):
    user = get_user_by_email(db, email)

    if user and check_password(password, user["password_hash"]):
        return user

    return None


# categories

def get_categories(db):
    return db.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()


# listings

LISTING_SELECT = """
    SELECT l.*,
           u.first_name || ' ' || u.last_name AS seller_name,
           c.name AS category_name,
           (
               SELECT image_path
               FROM listing_images i
               WHERE i.listing_id = l.id
               ORDER BY i.sort_order
               LIMIT 1
           ) AS cover_image
    FROM listings l
    JOIN users u ON u.id = l.seller_id
    JOIN categories c ON c.id = l.category_id
"""


def search_listings(db, query=None, category_id=None, limit=50):
    sql = LISTING_SELECT + " WHERE l.status = 'active'"
    params = []

    if query:
        sql += " AND (l.title ILIKE %s OR l.description ILIKE %s)"
        like = f"%{query}%"
        params += [like, like]

    if category_id:
        sql += " AND l.category_id = %s"
        params.append(category_id)

    sql += " ORDER BY l.created_at DESC, l.id DESC LIMIT %s"
    params.append(limit)

    return db.execute(sql, params).fetchall()


def get_listing(db, listing_id):
    return db.execute(
        LISTING_SELECT + " WHERE l.id = %s",
        (listing_id,)
    ).fetchone()


def get_listing_images(db, listing_id):
    return db.execute(
        """
        SELECT image_path
        FROM listing_images
        WHERE listing_id = %s
        ORDER BY sort_order
        """,
        (listing_id,)
    ).fetchall()


def get_listings_by_seller(db, seller_id):
    return db.execute(
        LISTING_SELECT + """
        WHERE l.seller_id = %s
          AND l.status != 'removed'
        ORDER BY l.created_at DESC
        """,
        (seller_id,)
    ).fetchall()


def create_listing(
    db, seller_id, category_id, title, price_cents,
    description="", condition="used", image_paths=()
):
    cur = db.execute(
        """
        INSERT INTO listings (
            seller_id, category_id, title, description,
            price_cents, condition
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            seller_id,
            category_id,
            title.strip(),
            description.strip(),
            price_cents,
            condition
        )
    )

    listing_id = cur.fetchone()["id"]

    if image_paths:
        with db.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO listing_images (listing_id, image_path, sort_order)
                VALUES (%s, %s, %s)
                """,
                [
                    (listing_id, path, i)
                    for i, path in enumerate(image_paths)
                ]
            )

    db.commit()
    return listing_id


def update_listing(
    db, listing_id, seller_id, category_id,
    title, price_cents, description, condition
):
    cur = db.execute(
        """
        UPDATE listings
        SET category_id = %s,
            title = %s,
            description = %s,
            price_cents = %s,
            condition = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
          AND seller_id = %s
          AND status = 'active'
        """,
        (
            category_id,
            title.strip(),
            description.strip(),
            price_cents,
            condition,
            listing_id,
            seller_id
        )
    )

    db.commit()
    return cur.rowcount > 0


def remove_listing(db, listing_id, seller_id):
    cur = db.execute(
        """
        UPDATE listings
        SET status = 'removed',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
          AND seller_id = %s
          AND status = 'active'
        """,
        (listing_id, seller_id)
    )

    db.commit()
    return cur.rowcount > 0


def set_listing_status(db, listing_id, seller_id, status):
    cur = db.execute(
        """
        UPDATE listings
        SET status = %s
        WHERE id = %s AND seller_id = %s
        """,
        (status, listing_id, seller_id)
    )

    db.commit()
    return cur.rowcount == 1


# favorites

def add_favorite(db, user_id, listing_id):
    db.execute(
        """
        INSERT INTO favorites (user_id, listing_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, listing_id) DO NOTHING
        """,
        (user_id, listing_id)
    )

    db.commit()


def remove_favorite(db, user_id, listing_id):
    db.execute(
        """
        DELETE FROM favorites
        WHERE user_id = %s AND listing_id = %s
        """,
        (user_id, listing_id)
    )

    db.commit()


def get_favorites(db, user_id):
    return db.execute(
        LISTING_SELECT + """
        JOIN favorites f ON f.listing_id = l.id
        WHERE f.user_id = %s
        ORDER BY f.created_at DESC
        """,
        (user_id,)
    ).fetchall()


# messaging

def get_or_create_conversation(db, listing_id, buyer_id):
    existing = db.execute(
        """
        SELECT id
        FROM conversations
        WHERE listing_id = %s AND buyer_id = %s
        """,
        (listing_id, buyer_id)
    ).fetchone()

    if existing:
        return existing["id"]

    cur = db.execute(
        """
        INSERT INTO conversations (listing_id, buyer_id)
        VALUES (%s, %s)
        RETURNING id
        """,
        (listing_id, buyer_id)
    )

    conversation_id = cur.fetchone()["id"]
    db.commit()

    return conversation_id


def send_message(db, conversation_id, sender_id, body):
    cur = db.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, body)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (conversation_id, sender_id, body.strip())
    )

    message_id = cur.fetchone()["id"]
    db.commit()

    return message_id


def get_messages(db, conversation_id):
    return db.execute(
        """
        SELECT m.*, u.first_name AS sender_name
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE m.conversation_id = %s
        ORDER BY m.sent_at, m.id
        """,
        (conversation_id,)
    ).fetchall()


def is_conversation_participant(db, conversation_id, user_id):
    row = db.execute(
        """
        SELECT 1
        FROM conversations c
        JOIN listings l ON l.id = c.listing_id
        WHERE c.id = %s
          AND (c.buyer_id = %s OR l.seller_id = %s)
        """,
        (conversation_id, user_id, user_id)
    ).fetchone()

    return row is not None


def get_conversations_for_user(db, user_id):
    return db.execute(
        """
        SELECT c.id, c.listing_id, l.title AS listing_title,
               c.buyer_id, l.seller_id,
               (
                   SELECT body
                   FROM messages m
                   WHERE m.conversation_id = c.id
                   ORDER BY m.sent_at DESC, m.id DESC
                   LIMIT 1
               ) AS last_message
        FROM conversations c
        JOIN listings l ON l.id = c.listing_id
        WHERE c.buyer_id = %s OR l.seller_id = %s
        ORDER BY c.created_at DESC
        """,
        (user_id, user_id)
    ).fetchall()
