# Nitter Tweet Tracker

## Overview

A simple standalone Python project for tracking tweets via a Nitter RSS feed. Stores data in a local SQLite database and provides a Flask-based web dashboard and API.

## Stack

- **Language**: Python 3.11
- **Web framework**: Flask
- **HTTP client**: requests
- **Scheduling**: schedule
- **Database**: SQLite (tweets.db)

## Project Files

- `main.py` — fetches tweets from Nitter RSS feeds and saves them to tweets.db
- `scheduler.py` — database-driven scheduler that automatically fetches tweets at configurable intervals
- `dashboard.py` — Flask web app with dashboard UI and REST API
- `migrate.py` — runs database schema migrations
- `tweets.db` — SQLite database
- `requirements.txt` — Python dependencies (requests, flask)
- `API_DOCS.md` — full REST API documentation

## Running

- **Dashboard**: `python dashboard.py` (runs on port 5000)
- **Fetch tweets once**: `python main.py`
- **Run scheduler**: `python scheduler.py`
- **Run migrations**: `python migrate.py`

## API Endpoints

- `GET /` — Dashboard UI
- `GET /user/<username>` — Per-user tweet view
- `GET /docs` — API documentation page
- `GET /api/stats` — Summary stats
- `GET /api/users` — List tracked users
- `POST /api/users` — Add a new user
- `GET /api/tweets` — All tweets (optional `?username=` filter)
- `GET /api/tweets/<username>` — Tweets for a specific user
