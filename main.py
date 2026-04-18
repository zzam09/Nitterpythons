import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import config
from db import get_connection, get_db_info

USERNAMES = ["nasa", "SpaceX", "elonmusk"]


# ── Database helpers ──────────────────────────────────────

def get_db_connection():
    return get_connection()


def setup_database(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracked_users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            username            TEXT UNIQUE NOT NULL,
            display_name        TEXT,
            is_active           INTEGER DEFAULT 1,
            last_fetched        TEXT,
            created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            fetch_interval_mins INTEGER DEFAULT 15,
            added_at            TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id     TEXT UNIQUE NOT NULL,
            username     TEXT NOT NULL,
            content      TEXT,
            x_url        TEXT NOT NULL,
            nitter_url   TEXT,
            published_at TEXT,
            is_retweet   INTEGER DEFAULT 0,
            saved_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def ensure_user_exists(conn, username):
    conn.execute(
        "INSERT OR IGNORE INTO tracked_users (username) VALUES (?)",
        (username,)
    )
    conn.commit()


def update_last_fetched(conn, username):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE tracked_users SET last_fetched = ? WHERE username = ?",
        (now, username)
    )
    conn.commit()


def tweet_exists(conn, tweet_id):
    row = conn.execute(
        "SELECT 1 FROM tweets WHERE tweet_id = ?", (tweet_id,)
    ).fetchone()
    return row is not None


def save_tweet(conn, tweet_id, username, content, x_url, nitter_url, published_at, is_retweet):
    """
    Persist one tweet with an immediate commit.
    Rolls back and raises RuntimeError on failure.
    """
    try:
        conn.execute("""
            INSERT INTO tweets (tweet_id, username, content, x_url, nitter_url, published_at, is_retweet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tweet_id, username, content, x_url, nitter_url, published_at, is_retweet))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to save tweet {tweet_id}: {e}") from e


# ── HTTP / Retry ──────────────────────────────────────────

def _is_retryable(exc):
    """Return True for transient errors worth retrying."""
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        # 4xx (except 429 Too Many Requests) are permanent — don't retry
        if status and 400 <= status < 500 and status != 429:
            return False
    return True


def fetch_rss_with_retry(url):
    """
    Fetch a URL with exponential-backoff retries.

    Retries on:
      - Network errors (timeout, connection refused, DNS failure)
      - HTTP 5xx server errors
      - HTTP 429 Too Many Requests

    Does NOT retry on HTTP 4xx client errors (except 429).
    Raises requests.exceptions.RequestException if all attempts fail.
    """
    delay = config.RETRY_DELAY
    last_exc = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as exc:
            last_exc = exc

            if not _is_retryable(exc):
                print(f"  Non-retryable error: {exc}")
                raise

            if attempt < config.MAX_RETRIES:
                print(f"  Attempt {attempt}/{config.MAX_RETRIES} failed: {exc}")
                print(f"  Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= config.RETRY_BACKOFF
            else:
                print(f"  Attempt {attempt}/{config.MAX_RETRIES} failed: {exc}")

    raise requests.exceptions.RequestException(
        f"All {config.MAX_RETRIES} attempts failed for {url}: {last_exc}"
    )


# ── Fetch logic ───────────────────────────────────────────

def fetch_tweets_for_user(conn, username):
    print(f"\nFetching tweets for @{username}...")
    rss_url = f"{config.NITTER_BASE}/{username}/rss"

    try:
        response = fetch_rss_with_retry(rss_url)
    except requests.exceptions.RequestException as e:
        print(f"  Could not fetch feed for @{username} after {config.MAX_RETRIES} attempts: {e}")
        return

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        print(f"  XML parse error for @{username}: {e}")
        return

    items = root.findall("./channel/item")
    new_count = skip_count = error_count = 0

    for item in items:
        link_el       = item.find("link")
        title_el      = item.find("title")
        pub_date_el   = item.find("pubDate")
        description_el = item.find("description")

        if link_el is None or not link_el.text:
            continue

        nitter_url = link_el.text.strip()
        if "/status/" not in nitter_url:
            continue

        tweet_id = nitter_url.split("/status/")[-1].strip("/").split("#")[0]
        x_url    = f"https://x.com/{username}/status/{tweet_id}"

        content = ""
        if title_el is not None and title_el.text:
            content = title_el.text.strip()
        elif description_el is not None and description_el.text:
            content = description_el.text.strip()

        is_retweet = 1 if content.startswith("RT @") else 0

        published_at = None
        if pub_date_el is not None and pub_date_el.text:
            published_at = pub_date_el.text.strip()

        if tweet_exists(conn, tweet_id):
            skip_count += 1
        else:
            try:
                save_tweet(conn, tweet_id, username, content, x_url,
                           nitter_url, published_at, is_retweet)
                print(f"  Saved: {x_url}")
                new_count += 1
            except RuntimeError as e:
                print(f"  {e} — skipping this tweet")
                error_count += 1

    # Mark user as fetched only after all tweets are safely committed
    update_last_fetched(conn, username)

    # Push all changes to Turso cloud before moving to the next user
    conn.sync()

    parts = [f"{new_count} new {'tweet' if new_count == 1 else 'tweets'} saved"]
    if skip_count:
        parts.append(f"{skip_count} skipped")
    if error_count:
        parts.append(f"{error_count} errors")
    print(f"Done for @{username} — {', '.join(parts)}")


def fetch_user(username):
    """
    Fetch one user with its own isolated connection.
    Fully committed and synced to Turso before returning.
    """
    conn = get_db_connection()
    setup_database(conn)
    ensure_user_exists(conn, username)
    try:
        fetch_tweets_for_user(conn, username)
    except Exception as e:
        print(f"  Unexpected error for @{username}: {e}")
        conn.rollback()
    finally:
        conn.close()


# ── Entry point ───────────────────────────────────────────

def main():
    config.validate()

    print("=" * 48)
    print(f"Tweet Fetch — {get_db_info()}")
    print(f"Nitter: {config.NITTER_BASE}")
    print(f"Retries: {config.MAX_RETRIES}  Timeout: {config.REQUEST_TIMEOUT}s  Backoff: {config.RETRY_BACKOFF}x")
    print("=" * 48)

    for username in USERNAMES:
        fetch_user(username)

    print("\n" + "=" * 48)
    print("All done.")
    print("=" * 48)


if __name__ == "__main__":
    main()
