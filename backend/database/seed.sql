-- =============================================================
-- Demo data so the site has something to show while we build it.
-- Every demo account's password is:  password123
-- =============================================================

INSERT INTO universities (id, name, email_domain) VALUES
    (1, 'Lakehead University', 'lakeheadu.ca');

INSERT INTO categories (id, name) VALUES
    (1, 'Textbooks'),
    (2, 'Electronics'),
    (3, 'Furniture'),
    (4, 'School Supplies'),
    (5, 'Clothing'),
    (6, 'Housing & Sublets'),
    (7, 'Other');

-- Hash of 'password123' made with db.hash_password()
INSERT INTO users (id, university_id, email, password_hash, first_name, last_name, bio, is_verified) VALUES
    (1, 1, 'shaan.demo@lakeheadu.ca',
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Shaan', 'Nabi', '3rd year CS. Selling old textbooks.', 1),
    (2, 1, 'zack.demo@lakeheadu.ca',
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Zack', 'Demo', NULL, 1),
    (3, 1, 'ahmed.demo@lakeheadu.ca',
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Ahmed', 'Ikki', NULL, 1),
    (4, 1, 'muhid.demo@lakeheadu.ca',
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Muhid', 'Demo', NULL, 1);

-- Prices are in cents: 4500 = $45.00
INSERT INTO listings (id, seller_id, category_id, title, description, price_cents, condition, status) VALUES
    (1, 1, 1, 'Intro to Algorithms (CLRS) 3rd Ed', 'Some highlighting, otherwise clean. Used for COMP 3413.', 4500, 'used', 'active'),
    (2, 2, 2, 'TI-84 Plus Calculator', 'Works perfectly, comes with batteries.', 6000, 'like_new', 'active'),
    (3, 3, 3, 'IKEA Desk + Chair', 'Pickup near campus only. Must go before end of term.', 8000, 'used', 'active'),
    (4, 4, 4, 'Engineering Graph Notebooks (x5)', 'Brand new, never opened.', 1500, 'new', 'active'),
    (5, 1, 2, 'Logitech Wireless Mouse', 'Already sold, keeping for history.', 1000, 'used', 'sold'),
    (6, 2, 6, 'Room Sublet - Winter Term', '5 min walk to campus, utilities included.', 65000, 'fair', 'active');

INSERT INTO listing_images (listing_id, image_path, sort_order) VALUES
    (1, '/static/uploads/clrs.jpg', 0),
    (2, '/static/uploads/ti84.jpg', 0),
    (3, '/static/uploads/desk_1.jpg', 0),
    (3, '/static/uploads/desk_2.jpg', 1);

INSERT INTO favorites (user_id, listing_id) VALUES
    (2, 1),
    (3, 1),
    (1, 3);

INSERT INTO conversations (id, listing_id, buyer_id) VALUES
    (1, 1, 2);

INSERT INTO messages (conversation_id, sender_id, body) VALUES
    (1, 2, 'Hey, is the CLRS book still available?'),
    (1, 1, 'Yep! Can meet at the ATAC building tomorrow.');
