import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from db import get_connection, DB_PATH, get_db_info

NITTER_BASE = "http://mail.tidebridges.com:8091"
USERNAMES = ["nasa", "SpaceX", "elonmusk"]


def get_db_connection():
    return get_connection()


def setup_database(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT UNIQUE NOT NULL,
            display_name TEXT,
            is_active    INTEGER DEFAULT 1,
            last_fetched TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
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
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO tracked_users (username) VALUES (?)",
        (username,)
    )
    conn.commit()


def update_last_fetched(conn, username):
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tracked_users SET last_fetched = ? WHERE username = ?",
        (now, username)
    )
    conn.commit()


def tweet_exists(conn, tweet_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tweets WHERE tweet_id = ?", (tweet_id,))
    return cursor.fetchone() is not None


def save_tweet(conn, tweet_id, username, content, x_url, nitter_url, published_at, is_retweet):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tweets (tweet_id, username, content, x_url, nitter_url, published_at, is_retweet)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tweet_id, username, content, x_url, nitter_url, published_at, is_retweet))
    conn.commit()


def fetch_tweets_for_user(conn, username):
    print(f"\nFetching tweets for @{username}...")
    rss_url = f"{NITTER_BASE}/{username}/rss"

    try:
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching feed for @{username}: {e}")
        return

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        print(f"  Error parsing XML for @{username}: {e}")
        return

    items = root.findall("./channel/item")
    new_count = 0

    for item in items:
        link_el = item.find("link")
        title_el = item.find("title")
        pub_date_el = item.find("pubDate")
        description_el = item.find("description")

        if link_el is None or not link_el.text:
            continue

        nitter_url = link_el.text.strip()

        if "/status/" not in nitter_url:
            continue

        tweet_id = nitter_url.split("/status/")[-1].strip("/").split("#")[0]
        x_url = f"https://x.com/{username}/status/{tweet_id}"

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
            print(f"  Skipped (already saved): {tweet_id}")
        else:
            save_tweet(conn, tweet_id, username, content, x_url, nitter_url, published_at, is_retweet)
            print(f"  Saved: {x_url}")
            new_count += 1

    update_last_fetched(conn, username)
    tweet_word = "tweet" if new_count == 1 else "tweets"
    print(f"Done for @{username} — {new_count} new {tweet_word} saved")


def fetch_user(username):
    conn = get_db_connection()
    setup_database(conn)
    ensure_user_exists(conn, username)
    try:
        fetch_tweets_for_user(conn, username)
    except Exception as e:
        print(f"  Unexpected error for @{username}: {e}")
    finally:
        conn.close()


def main():
    print("=" * 40)
    print("Starting tweet fetch...")
    print("=" * 40)

    conn = get_db_connection()
    setup_database(conn)

    for username in USERNAMES:
        ensure_user_exists(conn, username)
        try:
            fetch_tweets_for_user(conn, username)
        except Exception as e:
            print(f"  Unexpected error for @{username}: {e}")

    conn.close()

    print("\n" + "=" * 40)
    print(f"All done! Backend: {get_db_info()}")
    print("=" * 40)


if __name__ == "__main__":
    main()
