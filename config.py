import os
import sys


def _int(key, default):
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        print(f"[config] Warning: {key} is not a valid integer, using default {default}", file=sys.stderr)
        return int(default)


def _float(key, default):
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        print(f"[config] Warning: {key} is not a valid number, using default {default}", file=sys.stderr)
        return float(default)


# ── Database ──────────────────────────────────────────────
DB_PATH               = os.environ.get("DB_PATH", "tweets.db")
TURSO_DATABASE_URL    = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN      = os.environ.get("TURSO_AUTH_TOKEN", "")

# ── Nitter ────────────────────────────────────────────────
NITTER_BASE           = os.environ.get("NITTER_BASE", "http://mail.tidebridges.com:8091")

# ── HTTP / Retry ──────────────────────────────────────────
REQUEST_TIMEOUT       = _int("REQUEST_TIMEOUT", 15)   # seconds per request
MAX_RETRIES           = _int("MAX_RETRIES", 3)         # attempts before giving up
RETRY_DELAY           = _float("RETRY_DELAY", 2.0)     # initial wait between retries (seconds)
RETRY_BACKOFF         = _float("RETRY_BACKOFF", 2.0)   # multiplier applied after each failure

# ── Flask ─────────────────────────────────────────────────
FLASK_HOST            = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT            = _int("PORT", _int("FLASK_PORT", 5000))

# ── Scheduler ─────────────────────────────────────────────
SCHEDULER_SYNC_SECS   = _int("SCHEDULER_SYNC_SECS", 60)   # how often to re-read the DB for user changes
DEFAULT_FETCH_INTERVAL = _int("DEFAULT_FETCH_INTERVAL", 15) # minutes between fetches if not set per-user


def validate():
    """Print warnings for missing or suspicious config. Returns list of warning strings."""
    warnings = []

    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        warnings.append("Turso credentials not fully set — falling back to local SQLite")

    if not NITTER_BASE.startswith("http"):
        warnings.append(f"NITTER_BASE looks invalid: {NITTER_BASE!r}")

    if MAX_RETRIES < 1:
        warnings.append(f"MAX_RETRIES={MAX_RETRIES} is less than 1 — no retries will occur")

    if REQUEST_TIMEOUT < 1:
        warnings.append(f"REQUEST_TIMEOUT={REQUEST_TIMEOUT} is too low")

    for w in warnings:
        print(f"[config] Warning: {w}", file=sys.stderr)

    return warnings


def summary():
    """Return a human-readable config summary (no secrets)."""
    return {
        "db_path":               DB_PATH,
        "turso_url":             TURSO_DATABASE_URL or "(not set)",
        "turso_token_set":       bool(TURSO_AUTH_TOKEN),
        "nitter_base":           NITTER_BASE,
        "request_timeout_secs":  REQUEST_TIMEOUT,
        "max_retries":           MAX_RETRIES,
        "retry_delay_secs":      RETRY_DELAY,
        "retry_backoff":         RETRY_BACKOFF,
        "flask_host":            FLASK_HOST,
        "flask_port":            FLASK_PORT,
        "scheduler_sync_secs":   SCHEDULER_SYNC_SECS,
        "default_fetch_interval_mins": DEFAULT_FETCH_INTERVAL,
    }
