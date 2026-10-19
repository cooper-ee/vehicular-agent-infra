from pathlib import Path
import json
import sqlite3
import time


class Store:
    """Per-operation connections; one-process API serializes updates by session."""
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, history TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, result TEXT NOT NULL, expires REAL NOT NULL);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def history(self, session):
        with self.connect() as db:
            row = db.execute('SELECT history FROM sessions WHERE id=?', (session,)).fetchone()
        return json.loads(row[0]) if row else []

    def run(self, request_id):
        with self.connect() as db:
            row = db.execute('SELECT fingerprint,result FROM runs WHERE id=?', (request_id,)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def cached(self, key):
        with self.connect() as db:
            row = db.execute('SELECT result FROM cache WHERE key=? AND expires>?', (key, time.time())).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, request_id, fingerprint, result, session, history, cache_key, ttl):
        encoded = json.dumps(result, ensure_ascii=False)
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?)', (request_id, fingerprint, encoded, time.time()))
            db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?)', (session, json.dumps(history[-20:], ensure_ascii=False)))
            db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (cache_key, encoded, time.time() + ttl))
            db.execute('DELETE FROM cache WHERE expires<?', (time.time(),))
