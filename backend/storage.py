"""Small durable store. Original reports are immutable; annotations are separate."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, payload TEXT NOT NULL, PRIMARY KEY(kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, scan_id TEXT, payload TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            with db:
                db.execute('PRAGMA journal_mode=WAL')
                yield db
        finally:
            db.close()

    def put(self, kind, value):
        with self.lock, self.connect() as db:
            db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)', (kind, value['id'], json.dumps(value, ensure_ascii=False)))
        return value

    def get(self, kind, key):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM records WHERE kind=? AND id=?', (kind,key)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT payload FROM records WHERE kind=? ORDER BY rowid DESC', (kind,)).fetchall()
        return [json.loads(x[0]) for x in rows]

    def event(self, scan_id, event_name, **payload):
        event = {'type':event_name,'timestamp':now(),**payload}
        with self.lock, self.connect() as db:
            cur = db.execute('INSERT INTO events(scan_id,payload) VALUES (?,?)',(scan_id,json.dumps(event,ensure_ascii=False)))
            event['id'] = cur.lastrowid
        return event

    def events(self, scan_id, after=0):
        with self.connect() as db:
            rows = db.execute('SELECT seq,payload FROM events WHERE scan_id=? AND seq>? ORDER BY seq',(scan_id,after)).fetchall()
        return [{'id':i,**json.loads(p)} for i,p in rows]

    def recover(self):
        for scan in self.all('scan'):
            if scan['status'] in ('queued','running','cancelling'):
                scan.update(status='failed', error='Uygulama önceki kontrol tamamlanmadan kapandı.', completed_at=now(), analysis_complete=False)
                self.put('scan',scan)
                self.event(scan['id'],'interrupted',message=scan['error'])

    def new(self, record_kind, **fields):
        return self.put(record_kind, {'id':str(uuid4()), 'created_at':now(), **fields})
