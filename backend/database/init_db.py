"""
Build (or rebuild) the SQLite database from schema.sql + seed.sql.

    python backend/database/init_db.py            # schema + demo data
    python backend/database/init_db.py --no-seed  # empty tables only

WARNING: this wipes the existing database file.
"""

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE.parent / "lakehead_shop.db"


def init_db(seed=True):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))
    if seed:
        conn.executescript((HERE / "seed.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    print(f"Database ready at {DB_PATH}" + (" (with demo data)" if seed else ""))


if __name__ == "__main__":
    init_db(seed="--no-seed" not in sys.argv)
