import schedule
import time
from datetime import datetime

import config
from db import get_connection
from main import fetch_user

active_jobs = {}
_error_counts = {}   # username -> consecutive error count


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    print(f"[{now_str()}] {msg}", flush=True)


# ── Database ──────────────────────────────────────────────

def get_active_users_from_db():
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT username, fetch_interval_mins FROM tracked_users WHERE is_active = 1"
        ).fetchall()
        conn.close()
        return {
            row["username"]: row["fetch_interval_mins"] or config.DEFAULT_FETCH_INTERVAL
            for row in rows
        }
    except Exception as e:
        log(f"Error reading users from database: {e}")
        return {}


# ── Job factory ───────────────────────────────────────────

def make_job(username, job_holder):
    def job():
        log(f"Running scheduled fetch for @{username}...")
        try:
            fetch_user(username)
            _error_counts[username] = 0   # reset on success
        except Exception as e:
            count = _error_counts.get(username, 0) + 1
            _error_counts[username] = count
            log(f"Error fetching @{username} (consecutive failures: {count}): {e}")

            # After 5 consecutive failures, log a prominent warning
            if count >= 5:
                log(f"WARNING: @{username} has failed {count} times in a row — check the Nitter feed")

        if job_holder[0] and job_holder[0].next_run:
            log(f"Next fetch for @{username} at {job_holder[0].next_run.strftime('%H:%M')}")

    return job


# ── Scheduling ────────────────────────────────────────────

def schedule_user(username, interval_mins):
    job_holder = [None]
    j = schedule.every(interval_mins).minutes.do(make_job(username, job_holder))
    job_holder[0] = j
    active_jobs[username] = {"job": j, "interval": interval_mins}
    _error_counts.setdefault(username, 0)


def cancel_user(username):
    if username in active_jobs:
        schedule.cancel_job(active_jobs[username]["job"])
        del active_jobs[username]
    _error_counts.pop(username, None)


def sync_users():
    """Re-read the DB and add/remove/update scheduled jobs to match."""
    try:
        db_users = get_active_users_from_db()

        # Cancel jobs for users that were removed or deactivated
        for username in list(active_jobs.keys()):
            if username not in db_users:
                log(f"User removed or deactivated: @{username} — cancelling schedule")
                cancel_user(username)

        # Add or update jobs
        for username, interval in db_users.items():
            if username not in active_jobs:
                log(f"New user detected: @{username} — scheduling every {interval} min(s)")
                schedule_user(username, interval)
            elif active_jobs[username]["interval"] != interval:
                old = active_jobs[username]["interval"]
                log(f"Interval changed for @{username}: {old} → {interval} min(s)")
                cancel_user(username)
                schedule_user(username, interval)

    except Exception as e:
        log(f"Error during user sync: {e}")


# ── Entry point ───────────────────────────────────────────

def print_status():
    print("=" * 48)
    print("Scheduler started (database-driven)")
    db_users = get_active_users_from_db()
    if db_users:
        for username, interval in db_users.items():
            print(f"  @{username:<15} every {interval} min(s)")
    else:
        print("  No active users in database yet.")
    print(f"Re-syncing user list every {config.SCHEDULER_SYNC_SECS}s")
    print("=" * 48)


def main():
    config.validate()
    print_status()

    sync_users()
    schedule.every(config.SCHEDULER_SYNC_SECS).seconds.do(sync_users)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            log(f"Scheduler loop error: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
