# this builds the database file from schema.sql and seed.sql
# python init_db.py makes tables plus demo data
# python init_db.py --no-seed makes empty tables only
# it wipes whatever was in the db before

import sqlite3            # python's built in sqlite library
import sys                # lets us read stuff typed after the command
from pathlib import Path  # makes file paths work on any computer

HERE = Path(__file__).resolve().parent          # the folder this file is in
DB_PATH = HERE.parent / "lakehead_shop.db"      # db file goes one folder up in backend


def init_db(seed=True):
    conn = sqlite3.connect(DB_PATH)                                          # open the db, makes the file if it isnt there
    conn.execute("PRAGMA foreign_keys = ON")                                 # turn on foreign keys for this connection
    conn.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))   # read schema.sql and run all of it
    if seed:                                                                 # only add demo data if we want it
        conn.executescript((HERE / "seed.sql").read_text(encoding="utf-8")) # read seed.sql and run all of it
    conn.commit()                                                            # save everything
    conn.close()                                                             # close the db
    print(f"Database ready at {DB_PATH}" + (" (with demo data)" if seed else ""))  # let us know it worked


if __name__ == "__main__":                       # only runs when you run this file directly
    init_db(seed="--no-seed" not in sys.argv)    # seed unless you typed --no-seed
