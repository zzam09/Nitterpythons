import sqlite3
import config

try:
    import libsql_experimental as libsql
    _LIBSQL_AVAILABLE = True
except ImportError:
    _LIBSQL_AVAILABLE = False

DB_PATH    = config.DB_PATH
TURSO_URL  = config.TURSO_DATABASE_URL
TURSO_TOKEN = config.TURSO_AUTH_TOKEN

_USE_TURSO = _LIBSQL_AVAILABLE and bool(TURSO_URL) and bool(TURSO_TOKEN)


class _DictRow:
    """sqlite3.Row-compatible wrapper that works with both sqlite3 and libsql cursors."""
    def __init__(self, cursor_description, row):
        self._keys = [col[0] for col in cursor_description]
        self._row = row

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        return self._row[self._keys.index(key)]

    def __iter__(self):
        return iter(self._row)

    def keys(self):
        return self._keys

    def __len__(self):
        return len(self._row)


class _WrappedCursor:
    """Cursor wrapper that returns _DictRow objects."""
    def __init__(self, cursor):
        self._cur = cursor

    @property
    def description(self):
        return self._cur.description

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    def _wrap(self, row):
        if row is None:
            return None
        return _DictRow(self._cur.description, row)

    def execute(self, sql, params=()):
        self._cur.execute(sql, params)
        return self

    def fetchone(self):
        return self._wrap(self._cur.fetchone())

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        return [_DictRow(self._cur.description, r) for r in rows]

    def __iter__(self):
        for row in self._cur.fetchall():
            yield _DictRow(self._cur.description, row)


class _WrappedConnection:
    """Connection wrapper that injects _DictRow support regardless of backend."""
    def __init__(self, raw_conn, use_turso=False):
        self._conn = raw_conn
        self._use_turso = use_turso

    def cursor(self):
        return _WrappedCursor(self._conn.cursor())

    def execute(self, sql, params=()):
        cur = _WrappedCursor(self._conn.cursor())
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def sync(self):
        """Push local changes to Turso cloud. No-op for plain SQLite."""
        if self._use_turso:
            try:
                self._conn.sync()
            except Exception as e:
                print(f"  Warning: Turso sync failed: {e}")

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.close()


def get_connection() -> _WrappedConnection:
    if _USE_TURSO:
        raw = libsql.connect(
            database=DB_PATH,
            sync_url=TURSO_URL,
            auth_token=TURSO_TOKEN,
        )
        raw.sync()
    else:
        raw = sqlite3.connect(DB_PATH)

    return _WrappedConnection(raw, use_turso=_USE_TURSO)


def get_db_info() -> str:
    if _USE_TURSO:
        return f"Turso (libSQL) — {TURSO_URL}"
    return f"SQLite — {DB_PATH}"


if __name__ == "__main__":
    print(f"DB backend: {get_db_info()}")
    conn = get_connection()
    conn.execute("CREATE TABLE IF NOT EXISTS _ping (id INTEGER PRIMARY KEY)")
    conn.execute("DROP TABLE IF EXISTS _ping")
    conn.commit()
    conn.close()
    print("Connection OK")
