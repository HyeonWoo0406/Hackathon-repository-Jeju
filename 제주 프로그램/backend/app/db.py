import json
import os
import sqlite3
import sys
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar
from dotenv import load_dotenv

ROOT=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
ASSETS=Path(getattr(sys,'_MEIPASS',ROOT))
load_dotenv(ROOT/'.env')
if not getattr(sys,'frozen',False):load_dotenv(ROOT.parent.parent/'.env')
RESOURCE=ASSETS/'backend'/'app'
SETTINGS=json.loads((RESOURCE/'settings.json').read_text(encoding='utf-8'))
SESSION_DB=ContextVar('session_db',default=None)
PUBLIC_DB=ContextVar('public_db',default=None)

@contextmanager
def connect(path=None):
    path=Path(path or SESSION_DB.get() or os.getenv('WEEKLY_DB',str(ROOT/'data'/'app.db')))
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=30);con.row_factory=sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback();raise
    finally:con.close()

def public_connect():return connect(PUBLIC_DB.get())

def init():
    with connect() as c:
        c.executescript('''
CREATE TABLE IF NOT EXISTS store (id INTEGER PRIMARY KEY CHECK(id=1),name TEXT,emd TEXT NOT NULL,industry TEXT NOT NULL,stops TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sales (date TEXT PRIMARY KEY,amount INTEGER,closed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS stop_bus (date TEXT,station_id TEXT,boardings INTEGER,PRIMARY KEY(date,station_id));
CREATE TABLE IF NOT EXISTS wifi (date TEXT,emd TEXT,category TEXT,users INTEGER,PRIMARY KEY(date,emd,category));
CREATE TABLE IF NOT EXISTS island_bus (date TEXT PRIMARY KEY,boardings INTEGER);
CREATE TABLE IF NOT EXISTS weather (date TEXT,stn INTEGER,rain_mm REAL,max_ws REAL,PRIMARY KEY(date,stn));
CREATE TABLE IF NOT EXISTS holiday (date TEXT PRIMARY KEY,name TEXT);
CREATE TABLE IF NOT EXISTS fetch_log (source TEXT,key TEXT,date TEXT,rows INTEGER,fetched_at TEXT,PRIMARY KEY(source,key,date));
CREATE TABLE IF NOT EXISTS report (week_start TEXT PRIMARY KEY,body TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT);
''')
        c.executemany('INSERT OR IGNORE INTO holiday VALUES (?,?)',SETTINGS['holidays'].items())

def get_store():
    with connect() as c:r=c.execute('SELECT name,emd,industry,stops FROM store WHERE id=1').fetchone()
    if not r:return None
    r=dict(r);r['stops']=json.loads(r['stops']);return r
