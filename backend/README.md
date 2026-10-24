# Backend (Flask + SQLite)

## Setup (one time)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python backend/database/init_db.py
```

## Run
```bash
python backend/app.py
```
Open http://127.0.0.1:5000/api/listings

## Demo logins
Password for all of them is `password123`:
`shaan.demo@lakeheadu.ca`, `zack.demo@lakeheadu.ca`, `ahmed.demo@lakeheadu.ca`, `muhid.demo@lakeheadu.ca`

## Files
| file | what |
|---|---|
| `database/schema.sql` | all tables, triggers, indexes |
| `database/seed.sql` | demo data |
| `database/init_db.py` | rebuilds `lakehead_shop.db` (wipes it!) |
| `db.py` | every SQL query lives here |
| `app.py` | JSON API routes |

The `.db` file is gitignored. Everyone builds their own with `init_db.py`.
If you change `schema.sql`, re-run `init_db.py`.

## API
| method | route | login? |
|---|---|---|
| POST | `/api/register` `/api/login` `/api/logout` | |
| GET | `/api/me` | ✅ |
| GET | `/api/categories` | |
| GET | `/api/listings?q=&category=` | |
| GET | `/api/listings/<id>` | |
| POST | `/api/listings` | ✅ |
| POST | `/api/listings/<id>/status` (`active`/`sold`/`removed`) | ✅ |
| GET | `/api/users/<id>/listings` | |
| GET / POST / DELETE | `/api/favorites` · `/api/favorites/<listing_id>` | ✅ |
| GET | `/api/conversations` | ✅ |
| POST | `/api/listings/<id>/messages` (message the seller) | ✅ |
| GET / POST | `/api/conversations/<id>/messages` | ✅ |
