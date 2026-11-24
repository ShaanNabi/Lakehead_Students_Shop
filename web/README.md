# Lakehead Students Shop - website version

The same shop as the Java window, but it opens in a browser. No Java or javac needed.

## Run it (same steps for everyone)
```bash
git pull
python run.py
```
On a Mac use `python3 run.py`.

The first time, `run.py` sets everything up by itself:
1. makes a `.venv` and installs the packages
2. makes a secret key for you
3. asks you to paste the **database URL** once (get it from Zack in a private message, never in the group chat)
4. checks it can reach the database
5. starts the site and opens your browser

You will not see the URL while you paste it, that is normal. Press Enter.

After that it is just `python run.py`. Press `Ctrl + C` in the terminal to stop it.

Your settings are saved in a `.env` file. It is git-ignored, so it never goes on GitHub. `.env.example` shows what it looks like.

## If something goes wrong
| what you see | what to do |
|---|---|
| `Could not connect to the database` and mentions the Session pooler | your internet cannot reach the database directly. Ask Zack for the Session pooler URL, then run `python run.py --reset` and paste it |
| `password authentication failed` | the password changed. Ask Zack for the newest URL, then run `python run.py --reset` and paste it |
| `Heads up: this terminal has its own SUPABASE_DB_URL set` | an old `export` is still in that terminal. Close the tab and open a new one, or run `unset SUPABASE_DB_URL` |
| `Could not make a .venv here` | it still works, it uses your normal Python instead |
| `Port 5000 is already in use` | it picks the next free port by itself and prints the address |
| `python` not found on a Mac | use `python3 run.py` |
| you want to change the database URL | run `python run.py --reset` and paste the new one (your secret key stays the same) |

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
| `SECRET_KEY` | a long random string |
| `SUPABASE_DB_URL` | the database URL (set it in the host's dashboard, never in the code) |

On a host you set these in its dashboard instead of a `.env` file.
