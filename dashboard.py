import os
import re
from datetime import datetime
from flask import Flask, jsonify, request

from db import get_connection, DB_PATH, get_db_info

app = Flask(__name__)

BASE_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f13; color: #c9c9d4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; }
  a { color: #63cab7; text-decoration: none; }
  a:hover { text-decoration: underline; }
  h1 { color: #63cab7; font-size: 1.6rem; margin-bottom: 0.25rem; }
  h2 { color: #63cab7; font-size: 1.2rem; margin-bottom: 1rem; }
  .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }
  .top-bar { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 2rem; }
  .stat-box { background: #17171f; border: 1px solid #2a2a3a; border-radius: 8px; padding: 1rem 1.4rem; flex: 1; min-width: 140px; }
  .stat-box .label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
  .stat-box .value { font-size: 1.6rem; font-weight: 700; color: #63cab7; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.2rem; }
  .card { background: #17171f; border: 1px solid #2a2a3a; border-radius: 10px; padding: 1.4rem; }
  .card .username { font-size: 1.15rem; font-weight: 700; color: #63cab7; margin-bottom: 1rem; }
  .card .row { display: flex; justify-content: space-between; font-size: 0.88rem; padding: 0.3rem 0; border-bottom: 1px solid #1e1e2a; }
  .card .row:last-of-type { border-bottom: none; }
  .card .row .key { color: #888; }
  .card .row .val { font-weight: 600; }
  .btn { display: inline-block; margin-top: 1rem; background: #63cab7; color: #0f0f13; padding: 0.45rem 1.1rem; border-radius: 6px; font-size: 0.85rem; font-weight: 700; }
  .btn:hover { background: #7dddd0; text-decoration: none; }
  .back { display: inline-block; margin-bottom: 1.5rem; font-size: 0.88rem; color: #63cab7; }
  .count-label { font-size: 0.9rem; color: #888; margin-bottom: 1rem; }
  .empty { color: #888; font-style: italic; padding: 2rem 0; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  thead tr { background: #1e1e2a; }
  thead th { text-align: left; padding: 0.65rem 0.75rem; color: #63cab7; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }
  tbody tr:nth-child(odd) { background: #13131a; }
  tbody tr:nth-child(even) { background: #17171f; }
  tbody td { padding: 0.6rem 0.75rem; vertical-align: top; word-break: break-word; }
  .mono { font-family: 'SFMono-Regular', 'Consolas', monospace; font-size: 0.8rem; color: #aaa; }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.72rem; font-weight: 700; }
  .badge-rt { background: #2a2040; color: #a78bfa; }
  .badge-tw { background: #0d2a28; color: #63cab7; }
  .link-btn { display: inline-block; background: #1e2e2c; color: #63cab7; border: 1px solid #2a4a47; padding: 0.2rem 0.6rem; border-radius: 5px; font-size: 0.78rem; white-space: nowrap; }
  .link-btn:hover { background: #253d3a; text-decoration: none; }
  .page-title { margin-bottom: 0.5rem; }
  .sub { color: #888; font-size: 0.88rem; margin-bottom: 1.5rem; }
  .not-found { text-align: center; padding: 4rem 1rem; }
  .not-found h1 { font-size: 3rem; color: #2a2a3a; }
  .not-found p { color: #888; margin-top: 1rem; }
  @media (max-width: 600px) {
    .top-bar { flex-direction: column; }
    table { display: block; overflow-x: auto; }
  }
</style>
"""

def get_db():
    return get_connection()


def db_size_kb():
    try:
        return round(os.path.getsize(DB_PATH) / 1024, 1)
    except OSError:
        return 0


def run_migrations():
    conn = get_db()

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

    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(tracked_users)").fetchall()
    }

    if "fetch_interval_mins" not in existing:
        conn.execute("ALTER TABLE tracked_users ADD COLUMN fetch_interval_mins INTEGER DEFAULT 15")
        conn.commit()

    if "added_at" not in existing:
        conn.execute("ALTER TABLE tracked_users ADD COLUMN added_at TEXT")
        conn.execute(
            "UPDATE tracked_users SET added_at = created_at WHERE added_at IS NULL"
        )
        conn.commit()

    conn.execute(
        "UPDATE tracked_users SET fetch_interval_mins = 15 WHERE fetch_interval_mins IS NULL"
    )
    conn.commit()
    conn.close()


run_migrations()


@app.route("/")
def home():
    conn = get_db()

    total_tweets = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
    total_retweets = conn.execute("SELECT COUNT(*) FROM tweets WHERE is_retweet = 1").fetchone()[0]
    users = conn.execute("SELECT * FROM tracked_users ORDER BY username").fetchall()
    total_users = len(users)

    cards_html = ""
    for u in users:
        username = u["username"]
        tweet_count = conn.execute(
            "SELECT COUNT(*) FROM tweets WHERE username = ?", (username,)
        ).fetchone()[0]
        rt_count = conn.execute(
            "SELECT COUNT(*) FROM tweets WHERE username = ? AND is_retweet = 1", (username,)
        ).fetchone()[0]
        last_fetched = u["last_fetched"] or "Never"
        if last_fetched != "Never":
            last_fetched = last_fetched[:19].replace("T", " ")

        cards_html += f"""
        <div class="card">
          <div class="username">@{username}</div>
          <div class="row"><span class="key">Total tweets</span><span class="val">{tweet_count}</span></div>
          <div class="row"><span class="key">Retweets</span><span class="val">{rt_count}</span></div>
          <div class="row"><span class="key">Last fetched</span><span class="val">{last_fetched}</span></div>
          <a class="btn" href="/user/{username}">View Tweets</a>
        </div>
        """

    conn.close()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Tweet Tracker Dashboard</title>{BASE_STYLE}</head>
<body>
<div class="container">
  <h1>Tweet Tracker</h1>
  <p class="sub">Live stats from tweets.db</p>

  <div class="top-bar">
    <div class="stat-box"><div class="label">Users tracked</div><div class="value">{total_users}</div></div>
    <div class="stat-box"><div class="label">Total tweets</div><div class="value">{total_tweets}</div></div>
    <div class="stat-box"><div class="label">Retweets</div><div class="value">{total_retweets}</div></div>
    <div class="stat-box"><div class="label">Database size</div><div class="value">{db_size_kb()} KB</div></div>
  </div>

  <h2>Tracked Users</h2>
  <div class="cards">
    {cards_html if cards_html else '<p class="empty">No users tracked yet. Run main.py first.</p>'}
  </div>
</div>
</body>
</html>"""
    return html


@app.route("/user/<username>")
def user_tweets(username):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM tracked_users WHERE username = ?", (username,)
    ).fetchone()

    if user is None:
        conn.close()
        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>User Not Found</title>{BASE_STYLE}</head>
<body>
<div class="container">
  <div class="not-found">
    <h1>404</h1>
    <p>User <strong>@{username}</strong> not found in the database.</p>
    <a class="btn" href="/" style="margin-top:1.5rem;display:inline-block">← Back to dashboard</a>
  </div>
</div>
</body>
</html>"""
        return html, 404

    tweets = conn.execute(
        """SELECT tweet_id, content, is_retweet, published_at, x_url
           FROM tweets WHERE username = ?
           ORDER BY published_at DESC""",
        (username,)
    ).fetchall()
    conn.close()

    total = len(tweets)

    if total == 0:
        body = f'<p class="empty">No tweets saved yet for @{username}</p>'
    else:
        rows = ""
        for t in tweets:
            content = (t["content"] or "")[:100]
            if len(t["content"] or "") > 100:
                content += "…"
            pub = (t["published_at"] or "—")[:19]
            badge = '<span class="badge badge-rt">Retweet</span>' if t["is_retweet"] else '<span class="badge badge-tw">Tweet</span>'
            rows += f"""
            <tr>
              <td class="mono">{t['tweet_id']}</td>
              <td>{content}</td>
              <td>{badge}</td>
              <td class="mono">{pub}</td>
              <td><a class="link-btn" href="{t['x_url']}" target="_blank" rel="noopener">Open ↗</a></td>
            </tr>"""

        body = f"""
        <p class="count-label">{total} tweet{'s' if total != 1 else ''} saved</p>
        <table>
          <thead>
            <tr>
              <th>Tweet ID</th>
              <th>Content</th>
              <th>Type</th>
              <th>Published</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>@{username} — Tweet Tracker</title>{BASE_STYLE}</head>
<body>
<div class="container">
  <a class="back" href="/">← Back to dashboard</a>
  <h1 class="page-title">@{username}</h1>
  <p class="sub">All saved tweets, newest first</p>
  {body}
</div>
</body>
</html>"""
    return html


def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def fmt_ts(ts):
    if not ts:
        return None
    return ts[:19].replace("T", " ")


@app.route("/api/users")
def api_users():
    try:
        conn = get_db()
        users = conn.execute("SELECT * FROM tracked_users ORDER BY username").fetchall()
        result = []
        for u in users:
            username = u["username"]
            tweet_count = conn.execute(
                "SELECT COUNT(*) FROM tweets WHERE username = ?", (username,)
            ).fetchone()[0]
            rt_count = conn.execute(
                "SELECT COUNT(*) FROM tweets WHERE username = ? AND is_retweet = 1", (username,)
            ).fetchone()[0]
            result.append({
                "username": username,
                "display_name": u["display_name"],
                "is_active": u["is_active"],
                "last_fetched": fmt_ts(u["last_fetched"]),
                "tweet_count": tweet_count,
                "retweet_count": rt_count,
                "fetch_interval_mins": u["fetch_interval_mins"],
                "added_at": fmt_ts(u["added_at"]),
            })
        conn.close()
        return cors(jsonify(result))
    except Exception as e:
        return cors(jsonify({"error": str(e)})), 500


@app.route("/api/tweets")
def api_tweets():
    try:
        conn = get_db()
        username_filter = request.args.get("username")
        if username_filter:
            rows = conn.execute(
                """SELECT * FROM tweets WHERE username = ?
                   ORDER BY published_at DESC""",
                (username_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tweets ORDER BY published_at DESC"
            ).fetchall()
        conn.close()
        result = [dict(r) for r in rows]
        return cors(jsonify(result))
    except Exception as e:
        return cors(jsonify({"error": str(e)})), 500


@app.route("/api/tweets/<username>")
def api_tweets_by_user(username):
    try:
        conn = get_db()
        user = conn.execute(
            "SELECT 1 FROM tracked_users WHERE username = ?", (username,)
        ).fetchone()
        if user is None:
            conn.close()
            return cors(jsonify({"error": "User not found"})), 404
        rows = conn.execute(
            """SELECT * FROM tweets WHERE username = ?
               ORDER BY published_at DESC""",
            (username,)
        ).fetchall()
        conn.close()
        result = [dict(r) for r in rows]
        return cors(jsonify(result))
    except Exception as e:
        return cors(jsonify({"error": str(e)})), 500


@app.route("/api/stats")
def api_stats():
    try:
        conn = get_db()
        total_users = conn.execute("SELECT COUNT(*) FROM tracked_users").fetchone()[0]
        total_tweets = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
        total_retweets = conn.execute("SELECT COUNT(*) FROM tweets WHERE is_retweet = 1").fetchone()[0]
        last_updated_row = conn.execute(
            "SELECT MAX(last_fetched) FROM tracked_users"
        ).fetchone()[0]
        conn.close()
        return cors(jsonify({
            "total_users": total_users,
            "total_tweets": total_tweets,
            "total_retweets": total_retweets,
            "last_updated": fmt_ts(last_updated_row),
        }))
    except Exception as e:
        return cors(jsonify({"error": str(e)})), 500


@app.route("/api/users", methods=["POST"])
def api_add_user():
    try:
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip().lstrip("@")
        if not username:
            return cors(jsonify({"error": "username is required"})), 400

        display_name = (body.get("display_name") or "").strip() or None
        interval = int(body.get("fetch_interval_mins") or 15)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        existing = conn.execute(
            "SELECT 1 FROM tracked_users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            conn.close()
            return cors(jsonify({"error": "User already exists"})), 409

        conn.execute(
            """INSERT INTO tracked_users (username, display_name, fetch_interval_mins, added_at, is_active)
               VALUES (?, ?, ?, ?, 1)""",
            (username, display_name, interval, now),
        )
        conn.commit()
        conn.close()

        return cors(jsonify({
            "username": username,
            "display_name": display_name,
            "is_active": 1,
            "fetch_interval_mins": interval,
            "added_at": now,
        })), 201
    except Exception as e:
        return cors(jsonify({"error": str(e)})), 500


def render_markdown(md_text):
    """Convert markdown to styled HTML for the /docs page."""
    lines = md_text.split("\n")
    html_parts = []
    in_code = False
    code_buf = []
    code_lang = ""

    def flush_code():
        code = "\n".join(code_buf)
        code = (code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        lang_label = f'<span class="lang">{code_lang}</span>' if code_lang else ""
        return f'<div class="code-wrap">{lang_label}<pre><code>{code}</code></pre></div>'

    for line in lines:
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                code_buf = []
            else:
                html_parts.append(flush_code())
                in_code = False
                code_buf = []
                code_lang = ""
            continue

        if in_code:
            code_buf.append(line)
            continue

        if line.startswith("### "):
            html_parts.append(f'<h3>{inline_md(line[4:])}</h3>')
        elif line.startswith("## "):
            html_parts.append(f'<h2>{inline_md(line[3:])}</h2>')
        elif line.startswith("# "):
            html_parts.append(f'<h1>{inline_md(line[2:])}</h1>')
        elif line.startswith("---"):
            html_parts.append("<hr>")
        elif line.startswith("| "):
            html_parts.append(render_table_row(line))
        elif line.startswith("• ") or line.startswith("* "):
            html_parts.append(f'<li>{inline_md(line[2:])}</li>')
        elif line.strip() == "":
            html_parts.append('<div class="spacer"></div>')
        else:
            html_parts.append(f'<p>{inline_md(line)}</p>')

    result = "\n".join(html_parts)
    result = re.sub(r"(<li>.*?</li>)(\s*<li>)", r'<ul>\1\2', result)
    result = re.sub(r"(</li>)(?!\s*<li>)", r"\1</ul>", result)
    return result


def inline_md(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r'<code class="inline">\1</code>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render_table_row(line):
    if re.match(r"^\|[-| ]+\|$", line.strip()):
        return ""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    tag = "th" if any(c.strip() for c in cells) and line == line else "td"
    inner = "".join(f"<td>{inline_md(c)}</td>" for c in cells)
    return f"<tr>{inner}</tr>"


DOCS_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f13; color: #c9c9d4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.7; }
  .layout { display: flex; min-height: 100vh; }
  nav { width: 220px; flex-shrink: 0; background: #0a0a0f; border-right: 1px solid #1e1e2a; padding: 1.5rem 1rem; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
  nav .logo { color: #63cab7; font-weight: 700; font-size: 0.95rem; margin-bottom: 1.5rem; display: block; }
  nav a { display: block; color: #888; font-size: 0.82rem; padding: 0.3rem 0.5rem; border-radius: 4px; margin-bottom: 0.15rem; text-decoration: none; }
  nav a:hover { color: #63cab7; background: #17171f; }
  .content { flex: 1; max-width: 860px; padding: 3rem 2rem; }
  h1 { color: #63cab7; font-size: 1.9rem; margin-bottom: 0.5rem; border-bottom: 2px solid #1e1e2a; padding-bottom: 0.5rem; }
  h2 { color: #63cab7; font-size: 1.3rem; margin-top: 2.5rem; margin-bottom: 0.75rem; }
  h3 { color: #a0d4cb; font-size: 1.05rem; margin-top: 1.8rem; margin-bottom: 0.5rem; }
  p { margin-bottom: 0.5rem; font-size: 0.92rem; }
  hr { border: none; border-top: 1px solid #1e1e2a; margin: 2rem 0; }
  .spacer { height: 0.35rem; }
  ul { margin: 0.5rem 0 0.5rem 1.5rem; }
  li { font-size: 0.92rem; margin-bottom: 0.2rem; }
  a { color: #63cab7; }
  code.inline { background: #1a1a24; color: #a5e0d8; padding: 0.1em 0.4em; border-radius: 4px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.85em; }
  .code-wrap { background: #101018; border: 1px solid #1e1e2a; border-radius: 8px; margin: 0.75rem 0 1rem; overflow: hidden; position: relative; }
  .lang { position: absolute; top: 0.5rem; right: 0.75rem; font-size: 0.7rem; color: #555; font-family: monospace; text-transform: uppercase; }
  pre { overflow-x: auto; padding: 1.1rem 1.25rem; }
  pre code { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.82rem; color: #c9c9d4; background: none; white-space: pre; }
  table { width: 100%; border-collapse: collapse; margin: 0.75rem 0 1rem; font-size: 0.88rem; }
  tr:first-child td { background: #1e1e2a; color: #63cab7; font-weight: 600; }
  td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #1a1a24; }
  tr:nth-child(odd):not(:first-child) td { background: #13131a; }
  tr:nth-child(even):not(:first-child) td { background: #17171f; }
  strong { color: #e0e0f0; }
  @media (max-width: 700px) {
    .layout { flex-direction: column; }
    nav { width: 100%; height: auto; position: static; border-right: none; border-bottom: 1px solid #1e1e2a; }
    .content { padding: 1.5rem 1rem; }
  }
</style>
"""

NAV_LINKS = [
    ("Overview", "#top"),
    ("Base URL", "#base-url"),
    ("Authentication", "#authentication"),
    ("Response Format", "#response-format"),
    ("CORS", "#cors-support"),
    ("GET /api/stats", "#get-apistats"),
    ("GET /api/users", "#get-apiusers"),
    ("POST /api/users", "#post-apiusers"),
    ("GET /api/tweets", "#get-apitweets"),
    ("GET /api/tweets/{username}", "#get-apitweetsusername"),
    ("Frontend example", "#how-to-connect-to-a-frontend"),
    ("Add user form", "#how-to-add-a-new-user-from-a-frontend-form"),
]


def heading_id(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower().replace(" ", "-").replace("/", "").replace("{", "").replace("}", ""))


@app.route("/docs")
def docs():
    try:
        docs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "API_DOCS.md")
        with open(docs_path, "r", encoding="utf-8") as f:
            md = f.read()
    except FileNotFoundError:
        return "API_DOCS.md not found.", 404

    body_html = render_markdown(md)

    body_html = re.sub(
        r"<h([123])>(.+?)</h\1>",
        lambda m: f'<h{m.group(1)} id="{heading_id(m.group(2))}">{m.group(2)}</h{m.group(1)}>',
        body_html,
    )

    nav_html = "".join(f'<a href="{href}">{label}</a>' for label, href in NAV_LINKS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>API Docs — Tweet Tracker</title>{DOCS_STYLE}</head>
<body>
<div class="layout">
  <nav>
    <span class="logo">Tweet Tracker</span>
    <a href="/">← Dashboard</a>
    {nav_html}
  </nav>
  <div class="content" id="top">
    {body_html}
  </div>
</div>
</body>
</html>"""


def print_routes():
    print("\n" + "=" * 48)
    print("  Tweet Tracker — dashboard.py running")
    print("=" * 48)
    routes = sorted(
        [
            (list(rule.methods - {"HEAD", "OPTIONS"}), rule.rule)
            for rule in app.url_map.iter_rules()
            if rule.rule not in ("/static/<path:filename>",)
        ],
        key=lambda x: x[1],
    )
    for methods, path in routes:
        methods_str = ", ".join(sorted(methods))
        print(f"  {methods_str:<8}  {path}")
    print("=" * 48 + "\n")


if __name__ == "__main__":
    print_routes()
    app.run(host="0.0.0.0", port=5000, debug=False)
