# Nitter Tweet Tracker — API Documentation

## Base URL

When running locally:

```
http://localhost:5000
```

All API endpoints are prefixed with `/api`.

---

## Authentication

None. All endpoints are open with no keys or tokens required.

---

## Response Format

All API endpoints return **JSON**. HTML pages (`/`, `/user/{username}`, `/docs`) return HTML.

Successful responses use status `200` (or `201` for resource creation).
Error responses always include an `"error"` field explaining what went wrong.

```json
{ "error": "User not found" }
```

---

## CORS Support

Every API response includes:

```
Access-Control-Allow-Origin: *
```

This means you can call these endpoints from any browser, HTML file, or frontend app — no proxy or server needed.

---

## Endpoints

---

### GET /api/stats

Returns a summary of the entire database.

**Parameters:** None

**Example fetch() request:**

```js
const res = await fetch('http://localhost:5000/api/stats');
const data = await res.json();
console.log(data);
```

**Example curl request:**

```bash
curl http://localhost:5000/api/stats
```

**Example success response (200):**

```json
{
  "total_users": 3,
  "total_tweets": 59,
  "total_retweets": 12,
  "last_updated": "2026-04-18 10:30:00"
}
```

**Error responses:**

| Status | Body | Reason |
|--------|------|--------|
| 500 | `{"error": "..."}` | Database or server error |

---

### GET /api/users

Returns all tracked users with tweet counts and status.

**Parameters:** None

**Example fetch() request:**

```js
const res = await fetch('http://localhost:5000/api/users');
const users = await res.json();
users.forEach(u => console.log(u.username, u.tweet_count));
```

**Example curl request:**

```bash
curl http://localhost:5000/api/users
```

**Example success response (200):**

```json
[
  {
    "username": "nasa",
    "display_name": "NASA",
    "is_active": 1,
    "last_fetched": "2026-04-18 10:30:00",
    "tweet_count": 24,
    "retweet_count": 3,
    "fetch_interval_mins": 15,
    "added_at": "2026-04-18 03:02:15"
  }
]
```

**Error responses:**

| Status | Body | Reason |
|--------|------|--------|
| 500 | `{"error": "..."}` | Database or server error |

---

### POST /api/users

Adds a new user to the tracker. The scheduler will automatically start fetching their tweets on the next sync cycle (within 60 seconds).

**Request body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Twitter/X handle (without @) |
| display_name | string | No | Human-readable name |
| fetch_interval_mins | integer | No | How often to fetch in minutes. Default: 15 |

**Example fetch() request:**

```js
const res = await fetch('http://localhost:5000/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'github',
    display_name: 'GitHub',
    fetch_interval_mins: 30
  })
});
const data = await res.json();
console.log(data);
```

**Example curl request:**

```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "github", "display_name": "GitHub", "fetch_interval_mins": 30}'
```

**Example success response (201):**

```json
{
  "username": "github",
  "display_name": "GitHub",
  "is_active": 1,
  "fetch_interval_mins": 30,
  "added_at": "2026-04-18 10:35:00"
}
```

**Error responses:**

| Status | Body | Reason |
|--------|------|--------|
| 400 | `{"error": "username is required"}` | Missing username field |
| 409 | `{"error": "User already exists"}` | Username already in database |
| 500 | `{"error": "..."}` | Database or server error |

---

### GET /api/tweets

Returns all saved tweets sorted by `published_at` descending. Supports optional filtering by username.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | No | Filter tweets to one user only |

**Example fetch() request (all tweets):**

```js
const res = await fetch('http://localhost:5000/api/tweets');
const tweets = await res.json();
```

**Example fetch() request (filtered):**

```js
const res = await fetch('http://localhost:5000/api/tweets?username=nasa');
const tweets = await res.json();
```

**Example curl request:**

```bash
curl http://localhost:5000/api/tweets
curl "http://localhost:5000/api/tweets?username=SpaceX"
```

**Example success response (200):**

```json
[
  {
    "id": 1,
    "tweet_id": "1234567890123456789",
    "username": "nasa",
    "content": "Hubble captures a stunning new image...",
    "x_url": "https://x.com/nasa/status/1234567890123456789",
    "nitter_url": "http://mail.tidebridges.com:8091/nasa/status/1234567890123456789",
    "published_at": "Wed, 18 Apr 2026 10:00:00 GMT",
    "is_retweet": 0,
    "saved_at": "2026-04-18 10:05:00"
  }
]
```

**Error responses:**

| Status | Body | Reason |
|--------|------|--------|
| 500 | `{"error": "..."}` | Database or server error |

---

### GET /api/tweets/{username}

Returns all tweets for a specific user, sorted by `published_at` descending. Returns a 404 if the username does not exist in the database.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Twitter/X handle (without @) |

**Example fetch() request:**

```js
const res = await fetch('http://localhost:5000/api/tweets/nasa');
if (res.status === 404) {
  console.log('User not found');
} else {
  const tweets = await res.json();
}
```

**Example curl request:**

```bash
curl http://localhost:5000/api/tweets/nasa
```

**Example success response (200):**

```json
[
  {
    "id": 1,
    "tweet_id": "1234567890123456789",
    "username": "nasa",
    "content": "Hubble captures a stunning new image...",
    "x_url": "https://x.com/nasa/status/1234567890123456789",
    "nitter_url": "http://mail.tidebridges.com:8091/nasa/status/1234567890123456789",
    "published_at": "Wed, 18 Apr 2026 10:00:00 GMT",
    "is_retweet": 0,
    "saved_at": "2026-04-18 10:05:00"
  }
]
```

**Error responses:**

| Status | Body | Reason |
|--------|------|--------|
| 404 | `{"error": "User not found"}` | Username not in database |
| 500 | `{"error": "..."}` | Database or server error |

---

## How to connect to a frontend

Save the following as a standalone `.html` file and open it directly in any browser. No server or install needed — it calls your running tracker via the API.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tweet Viewer</title>
  <style>
    body { font-family: sans-serif; background: #0f0f13; color: #c9c9d4; padding: 2rem; }
    h1 { color: #63cab7; }
    select, button { padding: 0.5rem 1rem; font-size: 1rem; margin-right: 0.5rem; border-radius: 6px; border: none; cursor: pointer; }
    select { background: #17171f; color: #c9c9d4; border: 1px solid #2a2a3a; }
    button { background: #63cab7; color: #0f0f13; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; font-size: 0.9rem; }
    th { background: #1e1e2a; color: #63cab7; text-align: left; padding: 0.6rem; }
    tr:nth-child(odd) td { background: #13131a; }
    tr:nth-child(even) td { background: #17171f; }
    td { padding: 0.6rem; vertical-align: top; }
    a { color: #63cab7; }
    .status { margin-top: 1rem; color: #888; font-style: italic; }
  </style>
</head>
<body>
  <h1>Tweet Viewer</h1>

  <div>
    <select id="username">
      <option value="">-- Select a user --</option>
      <option value="nasa">@nasa</option>
      <option value="SpaceX">@SpaceX</option>
      <option value="elonmusk">@elonmusk</option>
    </select>
    <button onclick="loadTweets()">Load Tweets</button>
  </div>

  <p class="status" id="status"></p>
  <table id="tweet-table" style="display:none">
    <thead>
      <tr>
        <th>#</th>
        <th>Content</th>
        <th>Type</th>
        <th>Published</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody id="tweet-body"></tbody>
  </table>

  <script>
    const BASE = 'http://localhost:5000';

    async function loadTweets() {
      const username = document.getElementById('username').value;
      const status = document.getElementById('status');
      const table = document.getElementById('tweet-table');
      const tbody = document.getElementById('tweet-body');

      if (!username) {
        status.textContent = 'Please select a user.';
        return;
      }

      status.textContent = 'Loading...';
      table.style.display = 'none';
      tbody.innerHTML = '';

      try {
        const res = await fetch(`${BASE}/api/tweets/${username}`);
        if (res.status === 404) {
          status.textContent = `User @${username} not found.`;
          return;
        }
        const tweets = await res.json();
        if (tweets.length === 0) {
          status.textContent = `No tweets saved yet for @${username}.`;
          return;
        }
        tweets.forEach((t, i) => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td>${i + 1}</td>
            <td>${(t.content || '').substring(0, 120)}</td>
            <td>${t.is_retweet ? 'Retweet' : 'Tweet'}</td>
            <td>${(t.published_at || '').substring(0, 16)}</td>
            <td><a href="${t.x_url}" target="_blank">Open</a></td>
          `;
          tbody.appendChild(row);
        });
        status.textContent = `${tweets.length} tweets loaded for @${username}.`;
        table.style.display = 'table';
      } catch (err) {
        status.textContent = 'Error: could not reach the API. Is dashboard.py running?';
      }
    }
  </script>
</body>
</html>
```

---

## How to add a new user from a frontend form

Save the following as a standalone `.html` file. It posts to `POST /api/users` and shows a success or error message immediately.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Add Tracked User</title>
  <style>
    body { font-family: sans-serif; background: #0f0f13; color: #c9c9d4; padding: 2rem; max-width: 480px; margin: 0 auto; }
    h1 { color: #63cab7; margin-bottom: 1.5rem; }
    label { display: block; font-size: 0.85rem; color: #888; margin-bottom: 0.3rem; margin-top: 1rem; }
    input, select { width: 100%; padding: 0.5rem 0.75rem; font-size: 1rem; background: #17171f; color: #c9c9d4; border: 1px solid #2a2a3a; border-radius: 6px; }
    button { margin-top: 1.5rem; width: 100%; padding: 0.65rem; font-size: 1rem; background: #63cab7; color: #0f0f13; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }
    button:hover { background: #7dddd0; }
    .msg { margin-top: 1rem; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.9rem; display: none; }
    .msg.success { background: #0d2a28; color: #63cab7; border: 1px solid #2a4a47; }
    .msg.error { background: #2a1a1a; color: #f87171; border: 1px solid #4a2a2a; }
  </style>
</head>
<body>
  <h1>Add Tracked User</h1>

  <label for="username">Username (without @)</label>
  <input type="text" id="username" placeholder="e.g. github">

  <label for="display_name">Display Name (optional)</label>
  <input type="text" id="display_name" placeholder="e.g. GitHub">

  <label for="interval">Fetch Interval</label>
  <select id="interval">
    <option value="10">Every 10 minutes</option>
    <option value="15" selected>Every 15 minutes</option>
    <option value="20">Every 20 minutes</option>
    <option value="30">Every 30 minutes</option>
  </select>

  <button onclick="addUser()">Add User</button>

  <div class="msg" id="msg"></div>

  <script>
    const BASE = 'http://localhost:5000';

    async function addUser() {
      const username = document.getElementById('username').value.trim().replace(/^@/, '');
      const display_name = document.getElementById('display_name').value.trim();
      const fetch_interval_mins = parseInt(document.getElementById('interval').value);
      const msg = document.getElementById('msg');

      msg.style.display = 'none';
      msg.className = 'msg';

      if (!username) {
        showMsg('error', 'Username is required.');
        return;
      }

      try {
        const res = await fetch(`${BASE}/api/users`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, display_name: display_name || null, fetch_interval_mins })
        });
        const data = await res.json();
        if (res.ok) {
          showMsg('success', `@${data.username} added successfully! The scheduler will start fetching their tweets within 60 seconds.`);
          document.getElementById('username').value = '';
          document.getElementById('display_name').value = '';
        } else {
          showMsg('error', data.error || 'Something went wrong.');
        }
      } catch (err) {
        showMsg('error', 'Could not reach the API. Is dashboard.py running?');
      }
    }

    function showMsg(type, text) {
      const msg = document.getElementById('msg');
      msg.className = `msg ${type}`;
      msg.textContent = text;
      msg.style.display = 'block';
    }
  </script>
</body>
</html>
```
