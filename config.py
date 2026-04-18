import os
import sys
import json

SETTINGS_FILE = "settings.json"

# Settings that are editable from the UI panel (key → {label, type, default, hint})
EDITABLE = {
    "NITTER_BASE": {
        "label": "Nitter Base URL",
        "type":  "text",
        "default": "http://mail.tidebridges.com:8091",
        "hint": "Base URL of your Nitter instance",
    },
    "REQUEST_TIMEOUT": {
        "label": "Request Timeout (seconds)",
        "type":  "int",
        "default": 15,
        "hint": "Seconds before a fetch request is aborted",
    },
    "MAX_RETRIES": {
        "label": "Max Retries",
        "type":  "int",
        "default": 3,
        "hint": "How many times to retry a failed fetch",
    },
    "RETRY_DELAY": {
        "label": "Retry Delay (seconds)",
        "type":  "float",
        "default": 2.0,
        "hint": "Wait time before the first retry",
    },
    "RETRY_BACKOFF": {
        "label": "Retry Backoff Multiplier",
        "type":  "float",
        "default": 2.0,
        "hint": "Delay multiplier per retry (e.g. 2 = 2s → 4s → 8s)",
    },
    "SCHEDULER_SYNC_SECS": {
        "label": "Scheduler Sync Interval (seconds)",
        "type":  "int",
        "default": 60,
        "hint": "How often the scheduler re-reads the database for user changes",
    },
    "DEFAULT_FETCH_INTERVAL": {
        "label": "Default Fetch Interval (minutes)",
        "type":  "int",
        "default": 15,
        "hint": "Minutes between fetches for users with no custom interval",
    },
}


# ── Helpers ───────────────────────────────────────────────

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


def _load_file():
    """Read settings.json and return its contents as a dict."""
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"[config] Warning: Could not read {SETTINGS_FILE}: {e}", file=sys.stderr)
        return {}


def _resolve(key, cast, env_default):
    """Return value: settings.json → env var → hardcoded default."""
    overrides = _load_file()
    if key in overrides:
        try:
            return cast(overrides[key])
        except (ValueError, TypeError):
            pass
    try:
        return cast(os.environ.get(key, env_default))
    except (ValueError, TypeError):
        return cast(env_default)


# ── Settings (call reload() to re-read after file changes) ───

def reload():
    """Re-read settings.json and update all module-level config values in place."""
    import config as _self
    _self.NITTER_BASE            = _resolve("NITTER_BASE",            str,   "http://mail.tidebridges.com:8091")
    _self.REQUEST_TIMEOUT        = _resolve("REQUEST_TIMEOUT",        int,   15)
    _self.MAX_RETRIES            = _resolve("MAX_RETRIES",            int,   3)
    _self.RETRY_DELAY            = _resolve("RETRY_DELAY",            float, 2.0)
    _self.RETRY_BACKOFF          = _resolve("RETRY_BACKOFF",          float, 2.0)
    _self.SCHEDULER_SYNC_SECS    = _resolve("SCHEDULER_SYNC_SECS",    int,   60)
    _self.DEFAULT_FETCH_INTERVAL = _resolve("DEFAULT_FETCH_INTERVAL", int,   15)


def save_all(updates: dict):
    """
    Persist a dict of key→value overrides to settings.json and reload config.
    Only keys in EDITABLE are accepted; others are silently ignored.
    Pass {"_reset": True} to clear all overrides and fall back to env/defaults.
    """
    if updates.get("_reset"):
        with open(SETTINGS_FILE, "w") as f:
            json.dump({}, f)
        reload()
        return

    current = _load_file()
    for key, raw_value in updates.items():
        if key not in EDITABLE:
            continue
        meta = EDITABLE[key]
        try:
            if meta["type"] == "int":
                current[key] = int(raw_value)
            elif meta["type"] == "float":
                current[key] = float(raw_value)
            else:
                current[key] = str(raw_value).strip()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for {key}: {e}") from e

    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)

    reload()


def get_editable_with_values():
    """
    Return editable settings with their current value and source.
    Source is 'file' if overridden in settings.json, 'env' if set via env var,
    or 'default' otherwise.
    """
    file_data = _load_file()
    result = {}
    for key, meta in EDITABLE.items():
        if key in file_data:
            source = "file"
            value  = file_data[key]
        elif os.environ.get(key):
            source = "env"
            value  = os.environ.get(key)
        else:
            source  = "default"
            value   = meta["default"]
        result[key] = {**meta, "value": value, "source": source}
    return result


# ── Fixed (non-editable) settings ────────────────────────

DB_PATH            = os.environ.get("DB_PATH", "tweets.db")
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN   = os.environ.get("TURSO_AUTH_TOKEN", "")
FLASK_HOST         = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT         = _int("PORT", _int("FLASK_PORT", 5000))

# ── Editable settings (initial load) ─────────────────────
# These are set now and can be updated at runtime via reload()

NITTER_BASE            = _resolve("NITTER_BASE",            str,   "http://mail.tidebridges.com:8091")
REQUEST_TIMEOUT        = _resolve("REQUEST_TIMEOUT",        int,   15)
MAX_RETRIES            = _resolve("MAX_RETRIES",            int,   3)
RETRY_DELAY            = _resolve("RETRY_DELAY",            float, 2.0)
RETRY_BACKOFF          = _resolve("RETRY_BACKOFF",          float, 2.0)
SCHEDULER_SYNC_SECS    = _resolve("SCHEDULER_SYNC_SECS",    int,   60)
DEFAULT_FETCH_INTERVAL = _resolve("DEFAULT_FETCH_INTERVAL", int,   15)


# ── Validation / summary ──────────────────────────────────

def validate():
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
    return {
        "db_path":                    DB_PATH,
        "turso_url":                  TURSO_DATABASE_URL or "(not set)",
        "turso_token_set":            bool(TURSO_AUTH_TOKEN),
        "nitter_base":                NITTER_BASE,
        "request_timeout_secs":       REQUEST_TIMEOUT,
        "max_retries":                MAX_RETRIES,
        "retry_delay_secs":           RETRY_DELAY,
        "retry_backoff":              RETRY_BACKOFF,
        "flask_host":                 FLASK_HOST,
        "flask_port":                 FLASK_PORT,
        "scheduler_sync_secs":        SCHEDULER_SYNC_SECS,
        "default_fetch_interval_mins": DEFAULT_FETCH_INTERVAL,
    }
