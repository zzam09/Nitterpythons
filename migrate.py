import sqlite3

DB_PATH = "tweets.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    existing_users = {
        row[1]
        for row in conn.execute("PRAGMA table_info(tracked_users)").fetchall()
    }
    existing_tweets = {
        row[1]
        for row in conn.execute("PRAGMA table_info(tweets)").fetchall()
    }

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

    if "fetch_interval_mins" not in existing_users:
        conn.execute("ALTER TABLE tracked_users ADD COLUMN fetch_interval_mins INTEGER DEFAULT 15")
        print("Added column: fetch_interval_mins")

    if "added_at" not in existing_users:
        conn.execute("ALTER TABLE tracked_users ADD COLUMN added_at TEXT")
        conn.execute("UPDATE tracked_users SET added_at = created_at WHERE added_at IS NULL")
        print("Added column: added_at")

    conn.execute("UPDATE tracked_users SET fetch_interval_mins = 15 WHERE fetch_interval_mins IS NULL")
    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
