"""Validate WorkBuddy metadata, resources and package contents (stdlib only)."""
from pathlib import Path
import re
import sys
import zipfile

root = Path(__file__).resolve().parent
skill = root/'skills/workbuddy-short-video'
text = (skill/'SKILL.md').read_text(encoding='utf-8')
header = re.match(r'^---\n(.*?)\n---\n', text, re.S)
if not header: raise SystemExit('Missing frontmatter')
fields = dict(re.findall(r'^([a-z_\-]+):\s*(.+)$', header[1], re.M))
for key in ['name','description','description_zh','description_en','version','author']:
    if not fields.get(key): raise SystemExit('Missing WorkBuddy field: '+key)
if fields['name'] != skill.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', fields['name']):
    raise SystemExit('Invalid skill name')
for p in skill.rglob('*.md'):
    body = p.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', body):
        if '://' not in target and not (p.parent/target).is_file():
            raise SystemExit('Broken reference: '+target)
    if re.search(r'/Users/[^/]+/', body) or '[TODO:' in body:
        raise SystemExit('Personal path or unfinished scaffold: '+str(p))
for p in skill.rglob('*.py'):
    compile(p.read_text(encoding='utf-8'), str(p), 'exec')
for p in (root/'dist').glob('workbuddy-short-video-0.1.0*.zip'):
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        entry = 'workbuddy-short-video/SKILL.md' if '-folder' in p.stem else 'SKILL.md'
        if entry not in names: raise SystemExit('Missing entrypoint in '+p.name)
        if any('/../' in n or n.startswith('/') or '__pycache__' in n for n in names):
            raise SystemExit('Invalid archive member')
        if z.testzip(): raise SystemExit('Corrupt archive')
print('WorkBuddy metadata, references, Python syntax and available ZIP packages passed.')
