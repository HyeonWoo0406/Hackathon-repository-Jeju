from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
words=json.loads((ROOT/'backend/app/data/blocked.json').read_text(encoding='utf-8'))
issues=[]
for p in ROOT.rglob('*'):
    # Verification artifacts contain raw user questions, not application copy.
    if any(x in p.parts for x in ('.venv','node_modules','dist','build','__pycache__','models','output')) or p.suffix not in ('.py','.tsx','.ts','.css','.md','.html','.json'):continue
    if p.name in ('blocked.json','package-lock.json'):continue
    text='\n'.join(re.sub(r'[ \t]+','',line).casefold() for line in p.read_text(encoding='utf-8-sig').splitlines())
    for index,w in enumerate(words,1):
        if w.casefold() in text:issues.append(f'{p.relative_to(ROOT)}: rule {index}')
print('\n'.join(issues) if issues else f'PASS: {len(words)} active rules')
sys.exit(bool(issues))
