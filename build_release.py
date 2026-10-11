"""Create clean WorkBuddy installers and a shareable source archive."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parent
skill = root/'skills/workbuddy-short-video'
import re
version = re.search(r'^version:\s*(.+)$', (skill/'SKILL.md').read_text(encoding='utf-8'), re.M).group(1).strip()
dist = root/'dist'; dist.mkdir(exist_ok=True)
files = [p for p in skill.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for suffix, prefix in [('', ''), ('-folder', 'workbuddy-short-video/')]:
    target = dist/f'workbuddy-short-video-{version}{suffix}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files): z.write(p, prefix+p.relative_to(skill).as_posix())
        z.write(root/'LICENSE', prefix+'LICENSE')
source = dist/f'workbuddy-short-video-kit-source-{version}.zip'
with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.rglob('*')):
        if p.is_file() and not any(x in p.relative_to(root).parts for x in ['demo','dist','__pycache__','.git','.venv','.DS_Store']):
            z.write(p, 'workbuddy-short-video-kit/'+p.relative_to(root).as_posix())
beginner = dist/f'workbuddy-short-video-beginner-{version}.zip'
with zipfile.ZipFile(beginner, 'w', zipfile.ZIP_DEFLATED) as z:
    name = f'workbuddy-short-video-{version}.zip'
    z.write(dist/name, name)
    z.write(root/'三步安装说明.txt', '先读我-三步安装说明.txt')
    z.write(root/'开始剪辑-复制这句话.txt', '开始剪辑-复制这句话.txt')
    z.write(root/'docs/index.html', '领取与安装.html')
    z.write(root/'LICENSE', 'LICENSE')
checks = []
for p in sorted(dist.glob('*.zip')):
    checks.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
    print(p.name, p.stat().st_size)
(dist/'SHA256SUMS').write_text('\n'.join(checks)+'\n', encoding='utf-8')
