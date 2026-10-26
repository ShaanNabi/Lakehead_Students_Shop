-- this file makes all the tables for the shop
-- run it with python backend/database/init_db.py

-- sqlite turns foreign keys off by default so we turn them on
PRAGMA foreign_keys = ON;

-- delete old tables first so we always start fresh
-- children get dropped before parents or sqlite complains
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS listing_images;
DROP TABLE IF EXISTS listings;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS universities;


-- universities table so we can add more schools later
CREATE TABLE universities (
    id            INTEGER PRIMARY KEY,                           -- auto counts up like auto_increment in mysql
    name          TEXT NOT NULL UNIQUE,                          -- school name, no repeats
    email_domain  TEXT NOT NULL UNIQUE,                          -- like lakeheadu.ca
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP        -- sqlite has no date type so dates are text
);


-- every student account
CREATE TABLE users (
    id             INTEGER PRIMARY KEY,                          -- user id
    university_id  INTEGER NOT NULL REFERENCES universities(id), -- which school they go to
    email          TEXT NOT NULL UNIQUE COLLATE NOCASE,          -- unique and ignores caps so ABC and abc match
    password_hash  TEXT NOT NULL,                                -- scrambled password, never the real one
    first_name     TEXT NOT NULL,                                -- first name
    last_name      TEXT NOT NULL,                                -- last name
    bio            TEXT,                                         -- optional about me
    is_verified    INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)), -- no boolean in sqlite so 0 is no and 1 is yes
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP       -- when they signed up
);

-- trigger runs before a new user gets saved
-- it kills the insert if the email doesnt end with the school domain
CREATE TRIGGER users_email_domain_insert
BEFORE INSERT ON users
BEGIN
    SELECT RAISE(ABORT, 'Email must match your university domain') -- stop and throw this error
    WHERE lower(NEW.email) NOT LIKE '%@' || (                      -- NEW means the row being added, % means anything
        SELECT lower(email_domain) FROM universities WHERE id = NEW.university_id -- grab that school's domain
    );
END;

-- same check but for when someone edits their email or school
CREATE TRIGGER users_email_domain_update
BEFORE UPDATE OF email, university_id ON users
BEGIN
    SELECT RAISE(ABORT, 'Email must match your university domain') -- same error as above
    WHERE lower(NEW.email) NOT LIKE '%@' || (                      -- same domain check
        SELECT lower(email_domain) FROM universities WHERE id = NEW.university_id -- same lookup
    );
END;


-- item categories like textbooks or furniture
CREATE TABLE categories (
    id    INTEGER PRIMARY KEY,                                   -- category id
    name  TEXT NOT NULL UNIQUE                                   -- category name, no repeats
);


-- the stuff people are selling
CREATE TABLE listings (
    id            INTEGER PRIMARY KEY,                                         -- listing id
    seller_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,     -- who posted it, if they delete their account this goes too
    category_id   INTEGER NOT NULL REFERENCES categories(id),                  -- what category it's in
    title         TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),       -- title cant be empty or super long
    description   TEXT NOT NULL DEFAULT '',                                    -- details, blank if they skip it
    price_cents   INTEGER NOT NULL CHECK (price_cents >= 0),                   -- price in cents so 4599 is 45.99, no negatives
    condition     TEXT NOT NULL DEFAULT 'used'                                 -- item condition, used if not given
                  CHECK (condition IN ('new', 'like_new', 'used', 'fair')),    -- only these words allowed, works like enum
    status        TEXT NOT NULL DEFAULT 'active'                               -- new posts start active
                  CHECK (status IN ('active', 'sold', 'removed')),             -- only these 3 allowed
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,                     -- when it was posted
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP                      -- last time it got edited
);

-- auto updates updated_at whenever a listing changes
CREATE TRIGGER listings_touch_updated_at
AFTER UPDATE ON listings
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at                                           -- only if nobody set it already, stops an infinite loop
BEGIN
    UPDATE listings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;      -- stamp the time
END;


-- pics for each listing, one listing can have a bunch
CREATE TABLE listing_images (
    id          INTEGER PRIMARY KEY,                                           -- image id
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,    -- which listing, pics go if listing goes
    image_path  TEXT NOT NULL,                                                 -- where the file lives, we dont store the actual image
    sort_order  INTEGER NOT NULL DEFAULT 0                                     -- 0 shows first, then 1, 2 and so on
);


-- saved items, links users and listings together
CREATE TABLE favorites (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,       -- who saved it
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,    -- what they saved
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,                       -- when they saved it
    PRIMARY KEY (user_id, listing_id)                                          -- this pair is the key so you cant save the same thing twice
);


-- a chat between a buyer and a seller about one listing
CREATE TABLE conversations (
    id          INTEGER PRIMARY KEY,                                           -- chat id
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,    -- the item they're talking about
    buyer_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,       -- the buyer, seller comes from the listing
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,                       -- when the chat started
    UNIQUE (listing_id, buyer_id)                                              -- one chat per buyer per item
);

-- each message inside a chat
CREATE TABLE messages (
    id               INTEGER PRIMARY KEY,                                      -- message id
    conversation_id  INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, -- which chat it's in
    sender_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- who sent it
    body             TEXT NOT NULL CHECK (length(body) > 0),                   -- the text, cant be empty
    sent_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,                  -- when it was sent
    read_at          TEXT                                                      -- null means not read yet
);


-- indexes make searches faster, kinda like a book index
CREATE INDEX idx_listings_status_created ON listings(status, created_at DESC);    -- homepage feed of newest active stuff
CREATE INDEX idx_listings_category       ON listings(category_id);                -- filtering by category
CREATE INDEX idx_listings_seller         ON listings(seller_id);                  -- showing a user's listings
CREATE INDEX idx_listing_images_listing  ON listing_images(listing_id, sort_order); -- loading a listing's pics in order
CREATE INDEX idx_favorites_listing       ON favorites(listing_id);                -- counting who saved something
CREATE INDEX idx_messages_conversation   ON messages(conversation_id, sent_at);   -- loading a chat in order
CREATE INDEX idx_conversations_buyer     ON conversations(buyer_id);              -- finding a user's chats
