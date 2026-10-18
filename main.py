"""ElderGuard AI: local-first caregiver event API.
Run: uvicorn main:app --reload. No outbound messaging is performed.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager, contextmanager
import sqlite3, os, uuid, io, csv

ROOT = Path(__file__).parent
DB = Path(os.environ.get('ELDERGUARD_DB', str(ROOT / 'elderguard.db')))

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            'CREATE TABLE IF NOT EXISTS events ('
            'id TEXT PRIMARY KEY, '
            'timestamp TEXT NOT NULL, '
            'type TEXT NOT NULL, '
            'source TEXT NOT NULL, '
            'confidence REAL, '
            'details TEXT, '
            'resident TEXT NOT NULL, '
            'acknowledged INTEGER NOT NULL DEFAULT 0'
            ')'
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)')
        conn.commit()
    finally:
        conn.close()

def init():
    """Backward-compatible initialization helper."""
    init_db()

@contextmanager
def get_db():
    """Context manager ensuring SQLite connections are strictly closed on exit."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# Backward compatibility alias
connect = get_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title='ElderGuard AI API', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

class EventIn(BaseModel):
    type: Literal['fall_suspected','fall_confirmed','inactivity','manual_sos','recovered','monitoring_started','monitoring_stopped']
    source: Literal['browser_pose','pipegen','manual','simulation'] = 'manual'
    confidence: float | None = Field(default=None, ge=0, le=1)
    details: str = Field(default='', max_length=500)
    resident: str = Field(default='Resident 01', max_length=80)

class AcknowledgeIn(BaseModel):
    acknowledged: bool = True

@app.get('/')
def homepage(): return FileResponse(ROOT / 'static' / 'index.html')

@app.get('/api/health')
def health(): return {'ok': True, 'service': 'ElderGuard AI', 'pipeline': 'external_pipegen_not_connected_by_default'}

@app.post('/api/events', status_code=201)
def create_event(event: EventIn):
    item = {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'type': event.type,
        'source': event.source,
        'confidence': event.confidence,
        'details': event.details,
        'resident': event.resident,
        'acknowledged': False
    }
    with get_db() as c:
        c.execute(
            'INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',
            (item['id'], item['timestamp'], item['type'], item['source'], item['confidence'], item['details'], item['resident'], 0)
        )
    return item

@app.get('/api/events')
def list_events(limit: int = 100):
    limit = max(1, min(limit, 500))
    with get_db() as c:
        return [
            dict(row) | {'acknowledged': bool(row['acknowledged'])}
            for row in c.execute('SELECT * FROM events ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
        ]

@app.patch('/api/events/{event_id}/ack')
def acknowledge(event_id: str, inp: AcknowledgeIn):
    with get_db() as c:
        cur = c.execute('UPDATE events SET acknowledged=? WHERE id=?', (int(inp.acknowledged), event_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail='Event not found')
    return {'id': event_id, 'acknowledged': inp.acknowledged}

@app.get('/api/stats')
def stats():
    with get_db() as c:
        all_events = c.execute('SELECT count(*) FROM events').fetchone()[0]
        falls = c.execute("SELECT count(*) FROM events WHERE type in ('fall_suspected','fall_confirmed')").fetchone()[0]
        unresolved = c.execute("SELECT count(*) FROM events WHERE acknowledged=0 AND type in ('fall_suspected','fall_confirmed','manual_sos')").fetchone()[0]
    return {'total_events': all_events, 'fall_events': falls, 'open_alerts': unresolved}

@app.get('/api/events/export')
def export_events(limit: int = 1000):
    limit = max(1, min(limit, 5000))
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(['id', 'timestamp', 'type', 'source', 'confidence', 'resident', 'details', 'acknowledged'])
    with get_db() as c:
        rows = c.execute(
            'SELECT id, timestamp, type, source, confidence, resident, details, acknowledged FROM events ORDER BY timestamp DESC LIMIT ?',
            (limit,)
        ).fetchall()
        for row in rows:
            writer.writerow([
                row['id'],
                row['timestamp'],
                row['type'],
                row['source'],
                row['confidence'] if row['confidence'] is not None else '',
                row['resident'],
                row['details'],
                bool(row['acknowledged'])
            ])
    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="elderguard_incidents.csv"'}
    )
