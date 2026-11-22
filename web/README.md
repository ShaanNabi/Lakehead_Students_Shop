# Lakehead Students Shop - website version

The same shop as the Java window, but it opens in a browser. No Java or javac needed.

## Run it on your computer
```bash
source .venv/Scripts/activate
pip install -r requirements.txt
python backend/app.py
```
Then open http://127.0.0.1:5000

- The database builds itself the first time (with demo data).
- Demo logins, all with password `password123`:
  `shaan.demo@lakeheadu.ca`, `zack.demo@lakeheadu.ca`, `ahmed.demo@lakeheadu.ca`, `muhid.demo@lakeheadu.ca`
- Sign up needs a `@lakeheadu.ca` email.

## What is in here
| file | what it does |
|---|---|
| `index.html` | the page layout |
| `style.css` | the look (copies the Java window) |
| `app.js` | everything that happens in the browser: table, search, login, listing forms, chat |

The website only talks to the Flask `/api/...` urls. It never touches the database directly.

## Putting it online (not done yet)
Any host that runs Python works (Render, Railway, PythonAnywhere).

| setting | value |
|---|---|
| build command | `pip install -r requirements.txt` |
| start command | `gunicorn --preload --chdir backend app:app` (also in the `Procfile`) |
| `SECRET_KEY` | a long random string, required |
| `COOKIE_SECURE` | `1` (turns on the online safety checks below) |
| `SEED_DEMO_DATA` | `0` to skip the demo accounts |
| `DB_PATH` | where to keep the database file, ideally on a persistent disk |

What `COOKIE_SECURE=1` does:
- the app refuses to start without a `SECRET_KEY`
- `/api/dev-login` (login with only an email) is switched off
- the login cookie is only sent over https

Heads up: the database is a file on the server. Most free plans wipe it when the app restarts or redeploys. That is the gap the cloud database fixes.
