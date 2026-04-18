"""
APScheduler-based task scheduler with persistence.

Replaces the old schedule library with APScheduler BackgroundScheduler
for better persistence, Flask integration, and production readiness.
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import time
import requests
import sqlite3

import config
from db import get_connection, DB_PATH, get_db_info
from logger import get_logger, setup_logging, RequestContext, FunctionContext, log_function

# Setup structured logging
setup_logging("INFO")
logger = get_logger("scheduler")

# import fetch_user  # Will be imported when needed

# Configure logging for APScheduler
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

# Global scheduler instance
scheduler = None
_error_counts = {}   # username -> consecutive error count


def get_active_users_from_db():
    """Return dict of active users: {username: {id, interval}}"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, fetch_interval_mins FROM tracked_users WHERE is_active = 1"
    ).fetchall()
    conn.close()
    
    result = {}
    for row in rows:
        result[row['username']] = {
            'id': row['id'],
            'interval': row['fetch_interval_mins']
        }
    return result


def fetch_user_job(username):
    """Wrapper for fetch_user() that tracks errors."""
    # Import here to avoid circular import
    import main
    
    with RequestContext(user_id=username, context="scheduler_fetch"):
        with FunctionContext(logger, "fetch_user_job", username=username):
            try:
                # Reset error count on success
                _error_counts.pop(username, None)
                
                # Call the actual fetch function
                result = main.fetch_user(username)
                
                logger.info("Successfully fetched user", username=username, result=result)
                return result
                
            except Exception as e:
                # Increment error count
                _error_counts[username] = _error_counts.get(username, 0) + 1
                
                logger.error("Failed to fetch user", 
                           username=username, 
                           error=str(e), 
                           error_type=type(e).__name__,
                           consecutive_errors=_error_counts[username])
                
                # Re-raise for APScheduler to handle
                raise


def schedule_user(username, user_id, interval_mins):
    """Schedule a user's fetch job."""
    job_id = f"rss_job_{user_id}"
    
    scheduler.add_job(
        func=fetch_user_job,
        trigger='interval',
        minutes=interval_mins,
        args=[username],
        id=job_id,
        name=f"Fetch tweets for @{username}",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=900,
    )
    
    logger.info("Scheduled user job", 
               username=username, 
               user_id=user_id, 
               interval_minutes=interval_mins,
               job_id=job_id)


def cancel_user(username, user_id):
    """Cancel a user's scheduled job."""
    job_id = f"rss_job_{user_id}"
    
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info("Cancelled user job", username=username, user_id=user_id, job_id=job_id)
        else:
            logger.warn("No job found for user", username=username, user_id=user_id)
            
        _error_counts.pop(username, None)
        
    except Exception as e:
        logger.error("Error cancelling user job", 
                   username=username, 
                   user_id=user_id,
                   error=str(e),
                   error_type=type(e).__name__)


def sync_users():
    """
    Re-read the DB and add/remove/update scheduled jobs to match.
    This is the core logic that keeps the scheduler in sync with the database.
    """
    with RequestContext(context="scheduler_sync"):
        with FunctionContext(logger, "sync_users"):
            try:
                db_users = get_active_users_from_db()
                current_jobs = {job.id: job for job in scheduler.get_jobs()}
                
                logger.info("Starting user sync", 
                          db_user_count=len(db_users), 
                          current_job_count=len(current_jobs))
                
                # Remove jobs for users no longer in database
                for job_id, job in current_jobs.items():
                    if job_id == "sync_users_job":
                        continue  # Skip the sync job itself
                    
                    # Extract user_id from job_id
                    try:
                        user_id = int(job_id.split("_")[-1])
                        # Check if this user still exists in database
                        user_exists = any(
                            user_info['id'] == user_id 
                            for user_info in db_users.values()
                        )
                        
                        if not user_exists:
                            scheduler.remove_job(job_id)
                            logger.info("Removed job for deleted user", user_id=user_id, job_id=job_id)
                            
                    except (ValueError, IndexError):
                        logger.error("Invalid job ID format", job_id=job_id)
                
                # Add or update jobs for current users
                for username, user_info in db_users.items():
                    user_id = user_info['id']
                    interval = user_info['interval']
                    job_id = f"rss_job_{user_id}"
                    
                    if job_id not in current_jobs:
                        # New user - schedule them
                        logger.info("New user detected", 
                                  username=username, 
                                  user_id=user_id, 
                                  interval_minutes=interval)
                        schedule_user(username, user_id, interval)
                    else:
                        # Existing user - check if interval changed
                        existing_job = current_jobs[job_id]
                        existing_interval = existing_job.trigger.interval_length // 60  # Convert seconds to minutes
                        
                        if existing_interval != interval:
                            logger.info("Interval changed for user", 
                                      username=username, 
                                      user_id=user_id, 
                                      old_interval=existing_interval, 
                                      new_interval=interval)
                            schedule_user(username, user_id, interval)

            except Exception as e:
                logger.error("Error during user sync", 
                           error=str(e), 
                           error_type=type(e).__name__)


# ── Scheduler Lifecycle ───────────────────────────────────

def init_scheduler():
    """
    Initialize the APScheduler with job store and executors.
    This should be called once during application startup.
    """
    with RequestContext(context="scheduler_init"):
        with FunctionContext(logger, "init_scheduler"):
            global scheduler
            
            if scheduler is not None:
                logger.warn("Scheduler already initialized")
                return
            
            # Configure job store for persistence
            jobstores = {
                'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
            }
            
            # Configure thread pool executor
            executors = {
                'default': ThreadPoolExecutor(max_workers=10)
            }
            
            # Job defaults
            job_defaults = {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 900  # 15 minutes
            }
            
            # Create scheduler
            scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            logger.info("APScheduler initialized with SQLite job store", 
                      job_store='sqlite:///jobs.sqlite', 
                      max_workers=10)


def start_scheduler():
    """
    Start the scheduler and schedule the initial jobs.
    This should be called after Flask app creation.
    """
    with RequestContext(context="scheduler_start"):
        with FunctionContext(logger, "start_scheduler"):
            global scheduler
            
            if scheduler is None:
                logger.error("Scheduler not initialized - call init_scheduler() first")
                return
            
            # Start the scheduler
            scheduler.start()
            logger.info("APScheduler started")
            
            # Schedule the sync job
            scheduler.add_job(
                func=sync_users,
                trigger='interval',
                seconds=config.SCHEDULER_SYNC_SECS,
                id='sync_users_job',
                name='Sync users from database',
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=900,
            )
            
            logger.info("Scheduled user sync job", interval_seconds=config.SCHEDULER_SYNC_SECS)
            
            # Initial sync to schedule all users
            sync_users()
            
            logger.info("APScheduler startup complete", status="database-driven_with_persistence")
            print_status()


def stop_scheduler():
    """
    Stop the scheduler gracefully.
    This should be called during application shutdown.
    """
    with RequestContext(context="scheduler_stop"):
        with FunctionContext(logger, "stop_scheduler"):
            global scheduler
            
            if scheduler is None or not scheduler.running:
                logger.warn("Scheduler not running")
                return
            
            scheduler.shutdown(wait=True)
            logger.info("APScheduler stopped")


# ── Flask Integration ─────────────────────────────────────

def init_app(app):
    """
    Initialize scheduler with Flask app context.
    Call this after creating your Flask app.
    
    Example:
        app = Flask(__name__)
        init_app(app)
        start_scheduler()  # Start immediately
    """
    # Initialize scheduler
    init_scheduler()
    
    # Add scheduler info endpoint
    @app.route('/api/scheduler')
    def scheduler_status():
        """Return current scheduler status."""
        try:
            return {
                "scheduler": get_scheduler_info(),
                "error_counts": _error_counts
            }
        except Exception as e:
            return {"error": str(e)}, 500


def get_scheduler_info():
    """Get detailed scheduler information."""
    if scheduler is None:
        return {"status": "not_initialized"}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs_count": len(jobs),
        "jobs": jobs,
        "job_store": "sqlite:///jobs.sqlite"
    }


# ── Utility Functions ─────────────────────────────────────

def print_status():
    """Print current scheduler status to console."""
    info = get_scheduler_info()
    
    print("\n" + "="*50)
    print(f"  Active users:")
    for job in info["jobs"]:
        if job["id"].startswith("rss_job_"):
            print(f"    {job['name']} ({job['trigger']})")
    
    print(f"\n  Re-syncing user list every {config.SCHEDULER_SYNC_SECS}s")
    print(f"  Job store: {info['job_store']}")
    print("="*50)


# For backward compatibility with old print statements
def log(message):
    """Legacy log function - redirects to structured logger."""
    logger.info(message)
