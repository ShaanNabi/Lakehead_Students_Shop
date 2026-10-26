-- fake demo data so the site has stuff to show while we build it
-- every demo account's password is password123

-- add lakehead as school 1
INSERT INTO universities (id, name, email_domain) VALUES
    (1, 'Lakehead University', 'lakeheadu.ca');

-- add the categories people can pick from
INSERT INTO categories (id, name) VALUES
    (1, 'Textbooks'),
    (2, 'Electronics'),
    (3, 'Furniture'),
    (4, 'School Supplies'),
    (5, 'Clothing'),
    (6, 'Housing & Sublets'),
    (7, 'Other');

-- add our 4 demo users
-- the long string is password123 after db.hash_password() scrambled it
INSERT INTO users (id, university_id, email, password_hash, first_name, last_name, bio, is_verified) VALUES
    (1, 1, 'shaan.demo@lakeheadu.ca',                -- shaan
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Shaan', 'Nabi', '3rd year CS. Selling old textbooks.', 1),
    (2, 1, 'zack.demo@lakeheadu.ca',                 -- zack
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Zack', 'Demo', NULL, 1),
    (3, 1, 'ahmed.demo@lakeheadu.ca',                -- ahmed
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Ahmed', 'Ikki', NULL, 1),
    (4, 1, 'muhid.demo@lakeheadu.ca',                -- muhid
        'pbkdf2_sha256$600000$b4b809d56b53788ae0f9118fddf9c467$09593deca27fa546cb71688868c316794caadefdefccc4467366c6684bb6a207',
        'Muhid', 'Demo', NULL, 1);

-- add some listings, prices are in cents so 4500 is 45.00
-- columns go id, seller, category, title, description, price, condition, status
INSERT INTO listings (id, seller_id, category_id, title, description, price_cents, condition, status) VALUES
    (1, 1, 1, 'Intro to Algorithms (CLRS) 3rd Ed', 'Some highlighting, otherwise clean. Used for COMP 3413.', 4500, 'used', 'active'),   -- shaan's textbook
    (2, 2, 2, 'TI-84 Plus Calculator', 'Works perfectly, comes with batteries.', 6000, 'like_new', 'active'),                       -- zack's calculator
    (3, 3, 3, 'IKEA Desk + Chair', 'Pickup near campus only. Must go before end of term.', 8000, 'used', 'active'),                 -- ahmed's desk
    (4, 4, 4, 'Engineering Graph Notebooks (x5)', 'Brand new, never opened.', 1500, 'new', 'active'),                              -- muhid's notebooks
    (5, 1, 2, 'Logitech Wireless Mouse', 'Already sold, keeping for history.', 1000, 'used', 'sold'),                              -- sold one so we can test hiding it
    (6, 2, 6, 'Room Sublet - Winter Term', '5 min walk to campus, utilities included.', 65000, 'fair', 'active');                  -- zack's sublet

-- add pics, these files dont exist yet they're just paths
INSERT INTO listing_images (listing_id, image_path, sort_order) VALUES
    (1, '/static/uploads/clrs.jpg', 0),      -- textbook pic
    (2, '/static/uploads/ti84.jpg', 0),      -- calculator pic
    (3, '/static/uploads/desk_1.jpg', 0),    -- desk first pic
    (3, '/static/uploads/desk_2.jpg', 1);    -- desk second pic

-- some saved items, user then listing
INSERT INTO favorites (user_id, listing_id) VALUES
    (2, 1),     -- zack saved the textbook
    (3, 1),     -- ahmed saved the textbook
    (1, 3);     -- shaan saved the desk

-- zack starts a chat about shaan's textbook
INSERT INTO conversations (id, listing_id, buyer_id) VALUES
    (1, 1, 2);

-- the messages in that chat
INSERT INTO messages (conversation_id, sender_id, body) VALUES
    (1, 2, 'Hey, is the CLRS book still available?'),            -- zack asks
    (1, 1, 'Yep! Can meet at the ATAC building tomorrow.');      -- shaan replies
