"""Create empty databases for a clean submission install; never copy user data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,SESSION_DB,init
for name in ('demo-seed.db','public-data.db'):
    path=ROOT/'runtime'/name
    if path.exists():
        print('Preserved existing:',name)
        continue
    token=SESSION_DB.set(str(path))
    try:init()
    finally:SESSION_DB.reset(token)
    print('Created empty schema:',name)
print('No sales, stores, sessions, or fetched public data were copied.')
