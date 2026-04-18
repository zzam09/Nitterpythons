import schedule
import time
from datetime import datetime

from db import get_connection
from main import fetch_user

active_jobs = {}


def now_str():
    return datetime.now().strftime("%H:%M")


def get_active_users_from_db():
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT username, fetch_interval_mins FROM tracked_users WHERE is_active = 1"
        ).fetchall()
        conn.close()
        return {row["username"]: row["fetch_interval_mins"] or 15 for row in rows}
    except Exception as e:
        print(f"  [{now_str()}] Error reading users from database: {e}")
        return {}


def make_job(username, job_holder):
    def job():
        print(f"\n[{now_str()}] Running scheduled fetch for @{username}...")
        try:
            fetch_user(username)
        except Exception as e:
            print(f"  Error during scheduled fetch for @{username}: {e}")
        if job_holder[0] and job_holder[0].next_run:
            print(f"Next fetch for @{username} at {job_holder[0].next_run.strftime('%H:%M')}")
    return job


def schedule_user(username, interval_mins):
    job_holder = [None]
    j = schedule.every(interval_mins).minutes.do(make_job(username, job_holder))
    job_holder[0] = j
    active_jobs[username] = {"job": j, "interval": interval_mins}


def cancel_user(username):
    if username in active_jobs:
        schedule.cancel_job(active_jobs[username]["job"])
        del active_jobs[username]


def sync_users():
    try:
        db_users = get_active_users_from_db()

        for username in list(active_jobs.keys()):
            if username not in db_users:
                print(f"\n[{now_str()}] User removed or deactivated: @{username} — cancelling schedule")
                cancel_user(username)

        for username, interval in db_users.items():
            if username not in active_jobs:
                print(f"\n[{now_str()}] New user detected: @{username} — scheduling every {interval} mins")
                schedule_user(username, interval)
            elif active_jobs[username]["interval"] != interval:
                old = active_jobs[username]["interval"]
                print(f"\n[{now_str()}] Interval changed for @{username}: {old} → {interval} mins")
                cancel_user(username)
                schedule_user(username, interval)
    except Exception as e:
        print(f"  [{now_str()}] Error syncing users: {e}")


def print_status():
    print("=" * 40)
    print("Scheduler started (database-driven)")
    db_users = get_active_users_from_db()
    if db_users:
        for username, interval in db_users.items():
            print(f"  {username:<12} → every {interval} mins")
    else:
        print("  No active users found in database yet.")
    print("Refreshing user list every 60 seconds...")
    print("=" * 40)


def main():
    print_status()

    sync_users()

    schedule.every(60).seconds.do(sync_users)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
