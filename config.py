"""Configuration, read from the environment.

Settings live in the environment (or a .env file) rather than in a Python
module, so that one image can serve several groups with nothing but a different
env_file per container.

The legacy bot_secrets.py is still honoured as a fallback so existing
deployments keep working, but it is deprecated — set the environment variables
instead.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is a convenience for local dev, not a requirement
    pass

try:
    import bot_secrets as _legacy  # deprecated
except ImportError:
    _legacy = None


def _url(key: str, default: str = "") -> str:
    """A URL setting, guaranteed absolute.

    A schemeless host is a relative link once it lands in an email, and mail
    clients resolve it against the message rather than the web — Apple Mail
    turns it into an unopenable x-webdoc:// address. Prepending https is always
    the right repair: these are public callback URLs, and GroupMe requires TLS
    on them anyway.
    """
    value = _get(key, default).rstrip("/")
    if value and "://" not in value:
        value = "https://" + value
    return value


def _get(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    if value is not None:
        return value.strip()
    if _legacy is not None:
        return str(getattr(_legacy, key, default) or default).strip()
    return default


# --- GroupMe ---
BOT_ID = _get("BOT_ID")
BOT_NAME = _get("BOT_NAME")
CLIENT_ID = _get("CLIENT_ID")
CLIENT_SECRET = _get("CLIENT_SECRET")
REDIRECT_URI = _url("REDIRECT_URI")

# --- Email ---
SMTP_SERVER = _get("SMTP_SERVER")
SMTP_PORT = int(_get("SMTP_PORT", "587") or 587)
SMTP_USERNAME = _get("SMTP_USERNAME")
SMTP_PASSWORD = _get("SMTP_PASSWORD")
FROM_ADDRESS = _get("FROM_ADDRESS")

# --- Dashboard ---
DASHBOARD_URL = _url("DASHBOARD_URL")

# --- Storage ---
DB_PATH = _get("DB_PATH", "messages.db")
CREDENTIALS_PATH = _get("CREDENTIALS_PATH", "credentials.json")

# --- Scheduling ---
TIMEZONE = _get("TIMEZONE", "America/New_York")

# Only these gate startup. Email is optional: a bot with no SMTP config still
# posts to GroupMe, it just logs an error instead of sending mail — which is
# what you want for a test instance.
REQUIRED = ["BOT_ID", "BOT_NAME", "CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI"]

EMAIL_SETTINGS = ["SMTP_SERVER", "SMTP_USERNAME", "SMTP_PASSWORD", "FROM_ADDRESS"]


def email_configured() -> bool:
    return all(globals().get(key) for key in EMAIL_SETTINGS)


def check_config():
    """Fail loudly at startup if anything required is missing."""
    missing = [key for key in REQUIRED if not globals().get(key)]
    if missing:
        raise ValueError(
            "Missing required configuration: " + ", ".join(missing) +
            "\nSet them in the environment or a .env file (see .env.example).")
