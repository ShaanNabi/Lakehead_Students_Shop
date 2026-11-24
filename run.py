# one command to set up and start the website
#     python run.py
# the first time it makes a .venv, installs the packages and asks for the database url
# after that it just starts the shop and opens your browser
# extra options:
#     --reset          type in a new database url (when Zack sends you a new one)
#     --setup-only     do the setup and checks but do not start the site
#     --no-browser     do not open the browser
#     --skip-db-check  skip the database connection test

import getpass          # asks for the database url without showing it on screen
import hashlib          # tells us when requirements.txt changed
import os               # file paths and environment variables
import secrets          # makes a random secret key
import socket           # checks if a port is already in use
import subprocess       # runs pip and the server
import sys              # python version, options typed after the command
import threading        # lets the browser open while the server runs
import time             # small waits
import webbrowser       # opens the browser

ROOT = os.path.dirname(os.path.abspath(__file__))        # the project folder
ENV_FILE = os.path.join(ROOT, ".env")                    # your private settings, never goes on github
REQS = os.path.join(ROOT, "requirements.txt")            # the list of packages we need
VENV_DIR = os.path.join(ROOT, ".venv")                   # the virtual environment folder
APP = os.path.join(ROOT, "backend", "app.py")            # the flask server


# prints a line right away, plain text only so every terminal can show it
def say(text=""):
    print(text, flush=True)


# prints an error and stops
def fail(text):
    say("")
    say("Error: " + text)
    sys.exit(1)


# the python inside .venv, the path is different on windows and mac
def venv_python():
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


# figures out which python to use, and makes the .venv if it needs to
def get_python():
    if sys.prefix != sys.base_prefix:                    # a venv is already active, just use it
        return sys.executable
    py = venv_python()
    if not os.path.exists(py):                           # no .venv yet
        say("Making a virtual environment (.venv)...")
        result = subprocess.run([sys.executable, "-m", "venv", VENV_DIR],
                                capture_output=True, text=True, errors="replace")
        if result.returncode != 0 or not os.path.exists(py):
            say("Could not make a .venv here (this happens in OneDrive and Google Drive folders).")
            say("No problem, using your normal Python instead.")
            return sys.executable
    return py


# installs the packages, but skips it if nothing changed since last time
def install_packages(py):
    with open(REQS, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()    # fingerprint of requirements.txt
    marker = os.path.join(VENV_DIR, ".requirements-installed") if py == venv_python() else None
    if marker and os.path.exists(marker):
        with open(marker) as f:
            if f.read() == digest:                       # same list as last time
                return
    say("Installing packages (the first time takes a minute)...")
    result = subprocess.run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", REQS])
    if result.returncode != 0:
        fail("Installing the packages failed. Check your internet and run python run.py again.")
    if marker:
        with open(marker, "w") as f:
            f.write(digest)                              # remember we installed this exact list


# reads every line of .env as a dict
def read_env():
    values = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip("'\"")
    return values


# saves one setting in .env, replacing the old line for that setting if there is one
def set_env_value(key, value):
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f if not l.strip().startswith(key + "=")]
    lines.append(key + "='" + value.replace("'", "\\'") + "'")       # single quotes keep special characters safe
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# a setting counts as missing if it is empty or still the placeholder from .env.example
def has_real_value(key):
    value = os.environ.get(key) or read_env().get(key, "")
    return bool(value) and not value.startswith(("paste-", "change-me"))


# asks for something without showing it on screen, falls back to normal input when there is no real terminal
def ask_hidden(prompt):
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return input(prompt)


# makes sure .env has a secret key and a database url, reset=True asks for a new url even if one is saved
def ensure_env(reset=False):
    if not has_real_value("SECRET_KEY"):
        set_env_value("SECRET_KEY", secrets.token_hex(32))           # random, so cookies are safe
        say("Made a secret key for you.")
    if reset or not has_real_value("SUPABASE_DB_URL"):
        say("")
        if reset:
            say("Resetting the database URL (your secret key stays the same).")
        say("Paste the database URL Zack gave you, then press Enter.")
        say("You will not see it while you paste, that is normal.")
        url = ask_hidden("Database URL: ").strip().strip("'\"")
        if not url.startswith(("postgresql://", "postgres://")):
            fail("That does not look like a database URL, it should start with postgresql://  Nothing was changed. Run python run.py --reset to try again.")
        set_env_value("SUPABASE_DB_URL", url)
        say("Saved to .env (it is git-ignored, so it never goes on GitHub).")


# warns if the terminal has its own SUPABASE_DB_URL, because that one beats the .env file
def warn_if_shell_url_differs():
    in_shell = os.environ.get("SUPABASE_DB_URL")
    in_file = read_env().get("SUPABASE_DB_URL")
    if in_shell and in_file and in_shell != in_file:
        say("")
        say("Heads up: this terminal has its own SUPABASE_DB_URL set (an old export command),")
        say("and it beats the one in .env. Close this terminal tab and open a new one,")
        say("or run  unset SUPABASE_DB_URL  and then python run.py again.")
        say("")


# swaps any secret out of a piece of text before we show it
def redact(text, secrets_to_hide):
    for secret in secrets_to_hide:
        if secret:
            text = text.replace(secret, "***")
    return text


# turns a database error into something a human can act on
def explain(error):
    low = error.lower()
    if "password authentication failed" in low:
        return ("The database password is wrong, or it was reset.\n"
                "Ask Zack for the newest URL, then run  python run.py --reset  and paste it.")
    if any(w in low for w in ("network is unreachable", "could not translate host", "getaddrinfo",
                              "name or service not known", "timeout", "timed out")):
        return ("Your internet cannot reach the database directly (it needs IPv6).\n"
                "Ask Zack for the Session pooler URL (Supabase > Connect > Session pooler),\n"
                "then run  python run.py --reset  and paste it.")
    if "connection refused" in low or "could not connect" in low:
        return "The database refused the connection. Check the URL with Zack, then run  python run.py --reset  and paste it."
    return "Something went wrong talking to the database."


# tries to connect to the database once, so problems show up here and not as a blank website
def check_database(py):
    code = (
        "import os\n"
        "from dotenv import load_dotenv\n"
        "load_dotenv(%r)\n"
        "import psycopg\n"
        "psycopg.connect(os.environ['SUPABASE_DB_URL'], sslmode='require', connect_timeout=10).close()\n"
    ) % ENV_FILE
    say("Checking the database connection...")
    result = subprocess.run([py, "-c", code], capture_output=True, text=True, errors="replace")
    if result.returncode == 0:
        say("Database connected.")
        return
    url = os.environ.get("SUPABASE_DB_URL") or read_env().get("SUPABASE_DB_URL", "")
    password = ""
    try:
        from urllib.parse import urlparse
        password = urlparse(url).password or ""
    except ValueError:
        pass
    last = [l for l in result.stderr.strip().splitlines() if l.strip()]
    error = redact(last[-1] if last else "unknown error", [url, password])
    fail("Could not connect to the database.\n" + explain(error) + "\n\n(" + error[:300] + ")")


# true if something is already listening on that port
def port_is_busy(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


# uses port 5000, or the next free one if 5000 is taken (macOS uses 5000 for AirPlay)
def pick_port():
    start = int(os.environ.get("PORT", 5000))
    for port in range(start, start + 10):
        if not port_is_busy(port):
            if port != start:
                say("Port %d is already in use (another copy of the shop, or AirPlay on a Mac)." % start)
                say("Using port %d instead." % port)
            return port
    fail("Ports %d to %d are all busy. Close other copies of the shop and try again." % (start, start + 9))


# opens the browser once the server is answering
def open_when_ready(port, child):
    for _ in range(40):
        if child.poll() is not None:                     # the server stopped, nothing to open
            return
        if port_is_busy(port):                           # busy here means the server is up
            webbrowser.open("http://127.0.0.1:%d" % port)
            return
        time.sleep(0.5)


# starts the server and waits until you stop it
def launch(py, port, open_browser=True):
    env = dict(os.environ, PORT=str(port))
    say("")
    say("Starting the shop at http://127.0.0.1:%d" % port)
    say("Leave this window open while you use the site. Press Ctrl+C to stop.")
    say("")
    child = subprocess.Popen([py, APP], cwd=ROOT, env=env)
    if open_browser:
        threading.Thread(target=open_when_ready, args=(port, child), daemon=True).start()
    try:
        return child.wait()
    except KeyboardInterrupt:                            # you pressed Ctrl+C
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
        say("")
        say("Stopped.")
        return 0


def main():
    args = sys.argv[1:]
    if sys.version_info < (3, 9):
        fail("You need Python 3.9 or newer. Yours is " + sys.version.split()[0] + ".")
    py = get_python()
    install_packages(py)
    ensure_env(reset="--reset" in args)
    warn_if_shell_url_differs()
    if "--skip-db-check" not in args:
        check_database(py)
    if "--setup-only" in args:
        say("Setup done. Start the shop any time with: python run.py")
        return 0
    return launch(py, pick_port(), "--no-browser" not in args)


if __name__ == "__main__":
    sys.exit(main())
