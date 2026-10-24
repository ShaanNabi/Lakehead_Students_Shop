-- =============================================================
-- Lakehead Students Shop - SQLite schema
-- Run via: python backend/database/init_db.py
--
-- SQLite vs MySQL quick notes:
--   * INTEGER PRIMARY KEY auto-increments (no AUTO_INCREMENT needed)
--   * No real DATETIME type, dates are stored as TEXT 'YYYY-MM-DD HH:MM:SS'
--   * No ENUM, so CHECK (col IN (...)) does the same job
--   * Foreign keys are OFF by default, every connection must run
--     PRAGMA foreign_keys = ON;  (db.py does this for you)
-- =============================================================

PRAGMA foreign_keys = ON;

-- Drop in reverse dependency order so a re-run starts clean
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS listing_images;
DROP TABLE IF EXISTS listings;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS universities;

-- -------------------------------------------------------------
-- Universities: lets us add more schools later.
-- Only users whose email ends in email_domain can sign up.
-- -------------------------------------------------------------
CREATE TABLE universities (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    email_domain  TEXT NOT NULL UNIQUE,          -- e.g. 'lakeheadu.ca'
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------------
-- Users
-- -------------------------------------------------------------
CREATE TABLE users (
    id             INTEGER PRIMARY KEY,
    university_id  INTEGER NOT NULL REFERENCES universities(id),
    email          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash  TEXT NOT NULL,                -- never store plain passwords
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    bio            TEXT,
    is_verified    INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)),  -- SQLite has no BOOLEAN
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Block any email that doesn't match the user's university domain.
-- A CHECK constraint can't look at another table, so we use a trigger.
CREATE TRIGGER users_email_domain_insert
BEFORE INSERT ON users
BEGIN
    SELECT RAISE(ABORT, 'Email must match your university domain')
    WHERE lower(NEW.email) NOT LIKE '%@' || (
        SELECT lower(email_domain) FROM universities WHERE id = NEW.university_id
    );
END;

CREATE TRIGGER users_email_domain_update
BEFORE UPDATE OF email, university_id ON users
BEGIN
    SELECT RAISE(ABORT, 'Email must match your university domain')
    WHERE lower(NEW.email) NOT LIKE '%@' || (
        SELECT lower(email_domain) FROM universities WHERE id = NEW.university_id
    );
END;

-- -------------------------------------------------------------
-- Categories (Textbooks, Electronics, Furniture, ...)
-- -------------------------------------------------------------
CREATE TABLE categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
);

-- -------------------------------------------------------------
-- Listings: the items for sale
-- Price is stored in cents (INTEGER) to avoid decimal rounding bugs.
-- $45.99 -> 4599
-- -------------------------------------------------------------
CREATE TABLE listings (
    id            INTEGER PRIMARY KEY,
    seller_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id   INTEGER NOT NULL REFERENCES categories(id),
    title         TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    description   TEXT NOT NULL DEFAULT '',
    price_cents   INTEGER NOT NULL CHECK (price_cents >= 0),
    condition     TEXT NOT NULL DEFAULT 'used'
                  CHECK (condition IN ('new', 'like_new', 'used', 'fair')),
    status        TEXT NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'sold', 'removed')),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Keep updated_at fresh on every edit
CREATE TRIGGER listings_touch_updated_at
AFTER UPDATE ON listings
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE listings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- -------------------------------------------------------------
-- Listing images: one listing can have many photos.
-- We store the file path/URL, not the image itself.
-- -------------------------------------------------------------
CREATE TABLE listing_images (
    id          INTEGER PRIMARY KEY,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    image_path  TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- -------------------------------------------------------------
-- Favorites: many-to-many between users and listings.
-- Composite primary key = a user can't favorite the same thing twice.
-- -------------------------------------------------------------
CREATE TABLE favorites (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, listing_id)
);

-- -------------------------------------------------------------
-- Messaging: one conversation per (listing, buyer).
-- The seller is found through listings.seller_id.
-- -------------------------------------------------------------
CREATE TABLE conversations (
    id          INTEGER PRIMARY KEY,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    buyer_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (listing_id, buyer_id)
);

CREATE TABLE messages (
    id               INTEGER PRIMARY KEY,
    conversation_id  INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body             TEXT NOT NULL CHECK (length(body) > 0),
    sent_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at          TEXT                         -- NULL = unread
);

-- -------------------------------------------------------------
-- Indexes: speed up the queries the site runs the most
-- -------------------------------------------------------------
CREATE INDEX idx_listings_status_created ON listings(status, created_at DESC);
CREATE INDEX idx_listings_category       ON listings(category_id);
CREATE INDEX idx_listings_seller         ON listings(seller_id);
CREATE INDEX idx_listing_images_listing  ON listing_images(listing_id, sort_order);
CREATE INDEX idx_favorites_listing       ON favorites(listing_id);
CREATE INDEX idx_messages_conversation   ON messages(conversation_id, sent_at);
CREATE INDEX idx_conversations_buyer     ON conversations(buyer_id);
