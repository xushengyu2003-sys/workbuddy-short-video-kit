#!/usr/bin/env python3
"""Portable local editing engine. Python 3.9+, FFmpeg; Pillow for captions."""
import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


def run(args, cwd=None, binary=False):
    p = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True, text=not binary)
    if p.returncode:
        raise ValueError((p.stderr.decode(errors='replace') if binary else p.stderr)[-4000:] or '工具执行失败')
    return p


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()


def tool(name):
    override = os.environ.get('WB_' + name.upper())
    candidates = [override, shutil.which(name), '/opt/homebrew/bin/' + name,
                  '/usr/local/bin/' + name]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise ValueError('缺少 ' + name + '；请按 references/setup.md 安装，或设置 WB_' + name.upper())


def number(value, label, minimum=0):
    if isinstance(value, bool):
        raise ValueError(label + ' 必须是数字')
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(label + ' 超出范围')
    return value


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def local_file(value, base):
    if re.match(r'^[a-z]+://', str(value), re.I):
        raise ValueError('执行引擎只接受本地文件；先取得授权并下载素材')
    p = Path(value).expanduser()
    p = (base / p if not p.is_absolute() else p).resolve()
    if not p.is_file():
        raise ValueError('文件不存在：' + str(p))
    return p


def probe(path):
    data = json.loads(run([tool('ffprobe'), '-v', 'error', '-show_format',
                          '-show_streams', '-of', 'json', path]).stdout)
    streams = data['streams']
    return {'path': str(Path(path).resolve()),
            'duration': float(data.get('format', {}).get('duration', 0)),
            'video': next((s for s in streams if s['codec_type'] == 'video'), None),
            'audio': next((s for s in streams if s['codec_type'] == 'audio'), None)}


def doctor():
    result = {'python': sys.executable, 'python_version': sys.version.split()[0], 'tools': {},
              'optional': {m: bool(importlib.util.find_spec(m))
                           for m in ['PIL', 'faster_whisper', 'edge_tts']}}
    for name in ['ffmpeg', 'ffprobe']:
        try:
            path = tool(name)
            result['tools'][name] = {'path': path, 'version': run([path, '-version']).stdout.splitlines()[0]}
        except ValueError as e:
            result['tools'][name] = {'error': str(e)}
    if 'path' in result['tools']['ffmpeg']:
        enc = run([tool('ffmpeg'), '-hide_banner', '-encoders']).stdout
        result['h264_encoder'] = 'libx264' in enc
        result['h264_videotoolbox'] = 'h264_videotoolbox' in enc
    result['font'] = find_font(required=False)
    return result


def silence_keep(path, threshold=-35, minimum=0.6, padding=0.15):
    meta = probe(path)
    if not meta['audio']:
        raise ValueError('素材没有音轨；不能按静音判断剪辑点')
    log = run([tool('ffmpeg'), '-hide_banner', '-nostdin', '-i', path,
               '-map', '0:a:0', '-vn', '-af',
               f'silencedetect=noise={threshold}dB:d={minimum}', '-f', 'null', '-']).stderr
    intervals, start = [], None
    for line in log.splitlines():
        a = re.search(r'silence_start: ([\d.]+)', line)
        b = re.search(r'silence_end: ([\d.]+)', line)
        if a:
            start = float(a[1])
        if b and start is not None:
            intervals.append((start, float(b[1])))
            start = None
    if start is not None:
        intervals.append((start, meta['duration']))
    keep, cursor = [], 0.0
    for a, b in intervals:
        left, right = a + padding, b - padding
        if right <= left:
            continue
        if left - cursor >= 0.08:
            keep.append({'start': round(cursor, 3), 'end': round(min(left, meta['duration']), 3)})
        cursor = max(cursor, right)
    if meta['duration'] - cursor >= 0.08:
        keep.append({'start': round(cursor, 3), 'end': round(meta['duration'], 3)})
    return {'source': str(Path(path).resolve()), 'duration': meta['duration'], 'keep': keep,
            'silences': [{'start': a, 'end': b} for a, b in intervals],
            'warning': '静音检测不是语义理解；请结合转录和画面审核，勿据此自动选精彩段落。'}


def stamp(seconds):
    n = max(0, round(seconds * 1000))
    return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'


def srt_write(path, cues):
    Path(path).write_text('\n\n'.join(f'{i}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}'
                                     for i, c in enumerate(cues, 1)) + '\n', encoding='utf-8')


def srt_read(path):
    text = Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    cues = []
    pat = r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)'
    for block in re.split(r'\n\s*\n', text.strip()):
        m = re.search(pat, block)
        if not m:
            raise ValueError('SRT 时间格式错误')
        v = list(map(int, m.groups()))
        a, b = [v[k]*3600 + v[k+1]*60 + v[k+2] + v[k+3]/1000 for k in [0, 4]]
        body = block[m.end():].strip()
        if b <= a or not body:
            raise ValueError('SRT 存在空文本或无效区间')
        cues.append({'start': a, 'end': b, 'text': body})
    return cues


def remap(cues, clips):
    out, offset = [], 0.0
    for clip in clips:
        for cue in cues:
            a, b = max(cue['start'], clip['start']), min(cue['end'], clip['end'])
            if b - a > 0.03:
                out.append({'start': a-clip['start']+offset, 'end': b-clip['start']+offset,
                            'text': cue['text']})
        offset += clip['end'] - clip['start']
    return sorted(out, key=lambda c: c['start'])


def validate(manifest_path):
    base = Path(manifest_path).resolve().parent
    m = read_json(manifest_path)
    if m.get('schema_version') != 1:
        raise ValueError('schema_version 必须为 1')
    w, h = m.get('width', 1080), m.get('height', 1920)
    if not all(type(x) is int and 128 <= x <= 3840 and x % 2 == 0 for x in [w, h]):
        raise ValueError('宽高必须为 128–3840 范围的偶数整数')
    fps = number(m.get('fps', 30), 'fps', 1)
    if fps > 60:
        raise ValueError('fps 上限 60')
    if m.get('fit', 'contain') not in ['contain', 'cover']:
        raise ValueError('fit 必须为 contain 或 cover')
    if m.get('encoder', 'libx264') not in ['libx264', 'h264_videotoolbox']:
        raise ValueError('encoder 必须为 libx264 或 h264_videotoolbox')
    clips = m.get('clips', [])
    if not clips or len(clips) > 500:
        raise ValueError('clips 需要 1–500 个镜头')
    source_meta = {}
    for clip in clips:
        clip['source'] = str(local_file(clip['source'], base))
        clip['start'] = number(clip.get('start', 0), 'start')
        clip['end'] = number(clip['end'], 'end')
        if clip['end'] <= clip['start']:
            raise ValueError('镜头结束必须晚于开始')
        if clip.get('kind', 'video') not in ['video', 'image']:
            raise ValueError('kind 必须为 video 或 image')
        if clip.get('kind', 'video') == 'video':
            if clip['source'] not in source_meta: source_meta[clip['source']] = probe(clip['source'])
            meta = source_meta[clip['source']]
            if not meta['video'] or clip['end'] > meta['duration'] + 0.04:
                raise ValueError('视频无画面或裁切范围超过素材时长')
    duration = sum(c['end']-c['start'] for c in clips)
    if duration > 3600:
        raise ValueError('单次最多导出 1 小时；请拆成多条')
    for key in ['narration', 'music', 'subtitles', 'font']:
        if m.get(key):
            m[key] = str(local_file(m[key], base))
    if m.get('narration'):
        audio = probe(m['narration'])
        if not audio['audio'] or abs(audio['duration'] - duration) > 0.15:
            raise ValueError('配音与镜头总时长需对齐（误差不超过 0.15 秒）')
    if m.get('music') and not probe(m['music'])['audio']:
        raise ValueError('音乐文件没有音轨')
    gain = number(m.get('music_gain', 0.12), 'music_gain')
    if gain > 0.5:
        raise ValueError('music_gain 上限 0.5')
    cues = srt_read(m['subtitles']) if m.get('subtitles') else []
    timing = m.get('subtitle_timing', 'output')
    if timing not in ['output', 'source']:
        raise ValueError('subtitle_timing 必须为 output 或 source')
    if timing == 'source':
        if len({c['source'] for c in clips}) != 1 or any(c.get('kind', 'video') != 'video' for c in clips):
            raise ValueError('source 字幕仅适用于同一视频；多素材请先生成 output 字幕')
        cues = remap(cues, clips)
    for i, c in enumerate(cues):
        if c['end'] > duration + 0.05 or (i and c['start'] < cues[i-1]['end'] - 0.001):
            raise ValueError('字幕越界或重叠；请先校正时间轴')
    m['subtitle_style'] = subtitle_style(m.get('subtitle_style'))
    m.update(width=w, height=h, fps=fps, duration=duration, cues=cues)
    return m


def find_font(explicit=None, required=True):
    candidates = [explicit, os.environ.get('WB_FONT'),
                  '/System/Library/Fonts/PingFang.ttc',
                  '/System/Library/Fonts/STHeiti Medium.ttc',
                  'C:/Windows/Fonts/msyh.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for p in candidates:
        if p and Path(p).is_file():
            return str(Path(p).resolve())
    if required:
        raise ValueError('缺少中文字体，请在清单中指定 font 文件')
    return None


SUBTITLE_PRESETS = {
    'classic': {'font_size': 50, 'stroke_width': 3, 'color': '#FFFFFF', 'stroke_color': '#000000', 'position_y': 0.78, 'max_width': 0.78, 'line_spacing': 1.4},
    'readable': {'font_size': 60, 'stroke_width': 4, 'color': '#FFFFFF', 'stroke_color': '#000000', 'position_y': 0.78, 'max_width': 0.76, 'line_spacing': 1.25},
    'accent': {'font_size': 64, 'stroke_width': 4, 'color': '#FFE15A', 'stroke_color': '#151515', 'position_y': 0.76, 'max_width': 0.76, 'line_spacing': 1.25},
}


def subtitle_style(style=None):
    style = {} if style is None else style
    if not isinstance(style, dict):
        raise ValueError('subtitle_style 必须为对象')
    preset = style.get('preset', 'classic')
    if preset not in SUBTITLE_PRESETS:
        raise ValueError('未知字幕预设')
    unknown = set(style) - (set(SUBTITLE_PRESETS['classic']) | {'preset'})
    if unknown:
        raise ValueError('未知字幕参数：' + ','.join(sorted(unknown)))
    result = dict(SUBTITLE_PRESETS[preset]); result.update(style); result['preset'] = preset
    for key, low, high in [('font_size', 24, 100), ('stroke_width', 0, 10),
                           ('position_y', 0.15, 0.85), ('max_width', 0.4, 0.9), ('line_spacing', 1, 1.8)]:
        value = number(result[key], key, low)
        if value > high:
            raise ValueError('字幕参数超出范围：' + key)
    for key in ['color', 'stroke_color']:
        if not isinstance(result[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', result[key]):
            raise ValueError('字幕颜色必须为 #RRGGBB')
    return result


def subtitle_png(text, w, h, font_path, style=None):
    from PIL import Image, ImageDraw, ImageFont
    style = subtitle_style(style)
    size = max(12, round(w * style['font_size'] / 1080))
    stroke = round(w * style['stroke_width'] / 1080)
    font = ImageFont.truetype(font_path, size)
    im = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(im)
    lines, line = [], ''
    for ch in text.replace('\r', ''):
        if ch == '\n' or (line and draw.textlength(line+ch, font=font) > w*style['max_width'] - 2*stroke):
            lines.append(line)
            line = '' if ch == '\n' else ch
        else:
            line += ch
    if line:
        lines.append(line)
    if len(lines) > 2:
        raise ValueError('字幕超过两行，请依据词级时间戳拆分字幕，勿直接缩小字号')
    boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=stroke) for line in lines]
    step = size * style['line_spacing']
    total = (len(lines)-1)*step + (max((b[3]-b[1] for b in boxes), default=0))
    y = h*style['position_y'] - total/2
    for line, box in zip(lines, boxes):
        x = (w-(box[2]-box[0]))/2 - box[0]
        draw.text((x, y-box[1]), line, font=font, fill=style['color'],
                  stroke_width=stroke, stroke_fill=style['stroke_color'])
        y += step
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return buf.getvalue()


def h264_options(m):
    if m.get('encoder', 'libx264') == 'h264_videotoolbox':
        return ['-c:v', 'h264_videotoolbox', '-b:v', '6M', '-allow_sw', '0']
    return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '20']


def burn_captions(source, target, m):
    # Stream cached transparent PNGs: no dependence on libass or shell escaping.
    font = find_font(m.get('font'))
    images = [subtitle_png('', m['width'], m['height'], font, m.get('subtitle_style'))]
    images += [subtitle_png(c['text'], m['width'], m['height'], font, m.get('subtitle_style')) for c in m['cues']]
    # Decode only the subtitle band each frame, rather than a mostly empty full-frame PNG.
    from PIL import Image
    decoded = [Image.open(io.BytesIO(data)).convert('RGBA') for data in images]
    boxes = [im.getchannel('A').getbbox() for im in decoded]
    boxes = [box for box in boxes if box]
    top = max(0, min(box[1] for box in boxes)-2) if boxes else 0
    bottom = min(m['height'], max(box[3] for box in boxes)+2) if boxes else 2
    cropped = []
    for im in decoded:
        buf = io.BytesIO(); im.crop((0, top, m['width'], bottom)).save(buf, format='PNG')
        cropped.append(buf.getvalue())
    images = cropped
    args = [tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-i', source, '-f', 'image2pipe', '-framerate', str(m['fps']), '-vcodec', 'png', '-i', 'pipe:0',
            '-filter_complex_threads', '1',
            '-filter_complex', f'[0:v][1:v]overlay=y={top}:shortest=1:format=auto,format=yuv420p[v]',
            '-map', '[v]', '-map', '0:a', *h264_options(m),
            '-threads', '2', '-c:a', 'copy', '-movflags', '+faststart', target]
    with tempfile.TemporaryFile() as err:
        p = subprocess.Popen([str(x) for x in args], stdin=subprocess.PIPE, stderr=err)
        try:
            idx = 0
            for frame in range(math.ceil(m['duration']*m['fps'])):
                t = (frame+0.5)/m['fps']
                while idx < len(m['cues']) and t >= m['cues'][idx]['end']:
                    idx += 1
                active = idx < len(m['cues']) and m['cues'][idx]['start'] <= t < m['cues'][idx]['end']
                p.stdin.write(images[idx+1 if active else 0])
            p.stdin.close()
            code = p.wait()
        except Exception:
            p.kill()
            p.wait()
            err.seek(0)
            raise ValueError(err.read().decode(errors='replace')[-4000:] or '字幕渲染中断')
        if code:
            err.seek(0)
            raise ValueError(err.read().decode(errors='replace')[-4000:])


def render(manifest, out):
    started = time.perf_counter(); timings = {}
    m = validate(manifest)
    out = Path(out).expanduser().resolve()
    if out.exists():
        raise ValueError('输出目录已存在；请使用新的版本目录以保留原片')
    # Validate optional dependencies and layout before expensive rendering.
    if m['cues'] and m.get('burn_subtitles', True):
        if not importlib.util.find_spec('PIL'):
            raise ValueError('烧录字幕需要 Pillow；请按 setup.md 安装')
        font = find_font(m.get('font'))
        for cue in m['cues']:
            subtitle_png(cue['text'], m['width'], m['height'], font, m.get('subtitle_style'))
    out.mkdir(parents=True)
    w, h, fps = m['width'], m['height'], m['fps']
    with tempfile.TemporaryDirectory(prefix='wb-video-') as temp:
        temp = Path(temp)
        parts = []
        source_meta = {}
        for i, c in enumerate(m['clips']):
            d = c['end']-c['start']
            args = [tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y']
            image = c.get('kind', 'video') == 'image'
            if image:
                args += ['-loop', '1', '-framerate', str(fps), '-i', c['source']]
            else:
                args += ['-ss', str(c['start']), '-i', c['source']]
            if not image and c['source'] not in source_meta: source_meta[c['source']] = probe(c['source'])
            has_audio = not image and bool(source_meta[c['source']]['audio'])
            if not has_audio:
                args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
            if m.get('fit', 'contain') == 'cover':
                vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
            else:
                vf = f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101820'
            vf += f',setsar=1,fps={fps},format=yuv420p'
            part = temp / f'part{i:04}.mp4'
            args += ['-t', str(d), '-filter_threads', '1', '-vf', vf, '-map', '0:v:0', '-map', '0:a:0' if has_audio else '1:a:0',
                     '-af', 'aresample=48000,apad', *h264_options(m),
                     '-threads', '2', '-c:a', 'aac', '-ar', '48000', '-ac', '2', part]
            run(args)
            parts.append(part.name)
        (temp/'list.txt').write_text(''.join("file '"+name+"'\n" for name in parts), encoding='utf-8')
        joined = temp/'joined.mp4'
        run([tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-f', 'concat',
             '-safe', '1', '-i', 'list.txt', '-c', 'copy', joined], cwd=temp)
        mixed = temp/'mixed.mp4'
        args = [tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', joined]
        main_index = 0
        if m.get('narration'):
            args += ['-i', m['narration']]
            main_index = 1
        graph = f'[{main_index}:a]aresample=48000,apad,loudnorm=I=-16:TP=-1.5:LRA=11[a]'
        final_audio = '[a]'
        if m.get('music'):
            music_index = main_index+1
            args += ['-stream_loop', '-1', '-i', m['music']]
            graph += (f';[{music_index}:a]volume={m.get("music_gain",0.12)}[bg];'
                      '[a][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[ax]')
            final_audio = '[ax]'
        args += ['-filter_complex', graph, '-map', '0:v', '-map', final_audio,
                 '-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-t', str(m['duration']), mixed]
        run(args)
        timings['cut_and_mix_seconds'] = round(time.perf_counter()-started, 3)
        # Keep a caption-free, mixed base so a subtitle correction never repeats the cut/mix stage.
        shutil.copy2(mixed, out/'base.mp4')
        final = out/'final.mp4'
        if m['cues']:
            srt_write(out/'subtitles.srt', m['cues'])
        caption_start = time.perf_counter()
        if m['cues'] and m.get('burn_subtitles', True):
            burn_captions(mixed, final, m)
        else:
            run([tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                 '-i', mixed, '-c', 'copy', '-movflags', '+faststart', final])
        timings['captions_seconds'] = round(time.perf_counter()-caption_start, 3)
    write_json(out/'edit-plan.json', {k:v for k,v in m.items() if k != 'cues'})
    write_json(out/'base.json', {'role': 'caption_free_mixed_base', 'sha256': file_hash(out/'base.mp4'),
                               'plan_sha256': file_hash(out/'edit-plan.json')})
    check_start = time.perf_counter()
    report = quality(final, out/'review', expected=m['duration'], width=w, height=h)
    write_json(out/'quality.json', report)
    timings.update(quality_seconds=round(time.perf_counter()-check_start,3), total_seconds=round(time.perf_counter()-started,3))
    write_json(out/'timings.json', timings)
    return {'output': str(final), 'quality': report, 'timings': timings}


def restyle(previous, subtitles, out, preset=None, font_size=None):
    """Reuse only a receipted caption-free base. Never overlay new text on a burned final."""
    started = time.perf_counter(); previous = Path(previous).resolve(); out = Path(out).resolve()
    if out.exists(): raise ValueError('输出目录已存在，请使用新版本目录')
    receipt = read_json(previous/'base.json')
    if receipt.get('role') != 'caption_free_mixed_base' or file_hash(previous/'base.mp4') != receipt.get('sha256'):
        raise ValueError('无字幕底片缺失或已改变，不能复用')
    if file_hash(previous/'edit-plan.json') != receipt.get('plan_sha256'):
        raise ValueError('原清单已改变；剪辑或音乐变化须重新 render')
    m = read_json(previous/'edit-plan.json')
    m['subtitles'] = str(local_file(subtitles, Path.cwd())); m['subtitle_timing'] = 'output'; m['burn_subtitles'] = True
    m['cues'] = srt_read(m['subtitles'])
    if not m['cues']: raise ValueError('需要非空字幕')
    for i,c in enumerate(m['cues']):
        if c['end'] > m['duration']+0.05 or (i and c['start'] < m['cues'][i-1]['end']-0.001):
            raise ValueError('字幕越界或重叠')
    style = {'preset':preset} if preset else dict(m.get('subtitle_style',{}))
    if font_size is not None: style['font_size'] = font_size
    m['subtitle_style'] = subtitle_style(style)
    font = find_font(m.get('font'))
    for c in m['cues']: subtitle_png(c['text'],m['width'],m['height'],font,m['subtitle_style'])
    out.mkdir(parents=True)
    burn_captions(previous/'base.mp4',out/'final.mp4',m)
    caption_seconds = time.perf_counter()-started
    srt_write(out/'subtitles.srt',m['cues'])
    shutil.copy2(previous/'base.mp4',out/'base.mp4')
    write_json(out/'edit-plan.json',{k:v for k,v in m.items() if k!='cues'})
    write_json(out/'base.json',dict(receipt,plan_sha256=file_hash(out/'edit-plan.json')))
    report = quality(out/'final.mp4',out/'review',expected=m['duration'],width=m['width'],height=m['height'])
    write_json(out/'quality.json',report)
    timings = {'reused_base':True,'captions_seconds':round(caption_seconds,3),'total_seconds':round(time.perf_counter()-started,3)}
    write_json(out/'timings.json',timings)
    return {'output':str(out/'final.mp4'),'quality':report,'timings':timings}


def quality(path, review, expected=None, width=None, height=None):
    meta = probe(path)
    review = Path(review)
    review.mkdir(parents=True, exist_ok=True)
    failures = []
    v, a = meta['video'], meta['audio']
    if not v or v.get('codec_name') != 'h264':
        failures.append('画面缺失或不是 H.264')
    if not a or a.get('codec_name') != 'aac':
        failures.append('音轨缺失或不是 AAC')
    if width and (v['width'] != width or v['height'] != height):
        failures.append('尺寸不符合清单')
    if expected is not None and abs(meta['duration']-expected) > max(0.15, expected*0.01):
        failures.append('时长与剪辑清单不符')
    for i, t in enumerate([0, meta['duration']*0.5, max(0, meta['duration']-0.1)]):
        run([tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
             '-ss', str(t), '-i', path, '-frames:v', '1', review/f'frame-{i}.jpg'])
    run([tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', path,
         '-f', 'null', '-'])
    return {'machine_pass': not failures, 'failures': failures, 'duration': meta['duration'],
            'width': v.get('width') if v else None, 'height': v.get('height') if v else None,
            'review_frames': str(review.resolve()), 'human_review': 'pending',
            'review_notes': '机器通过仅代表编码/解码/尺寸/时长；字幕字形、断句、语义、裁切、听感仍需检查。'}


def transcribe(path, out, model, allow_download=False, beam_size=1, glossary=None):
    from faster_whisper import WhisperModel
    out = Path(out)
    if out.exists():
        raise ValueError('转录输出已存在，请使用新目录')
    print('正在加载本地转录模型…', file=sys.stderr, flush=True)
    engine = WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=2,
                          local_files_only=not allow_download)
    segments, info = engine.transcribe(str(path), language='zh', vad_filter=True,
                                      word_timestamps=True, beam_size=beam_size, temperature=0,
                                      initial_prompt=glossary or None)
    cues, words = [], []
    print('正在识别中文语音，CPU 速度随机器而异…', file=sys.stderr, flush=True)
    for seg in segments:
        cues.append({'start': seg.start, 'end': seg.end, 'text': seg.text.strip()})
        for word in seg.words or []:
            words.append({'start': word.start, 'end': word.end, 'text': word.word, 'probability': word.probability})
        print(f'已识别至 {seg.end:.1f} 秒', file=sys.stderr, flush=True)
    if not cues:
        raise ValueError('未识别到可用语音；请检查音轨或提供校对后的字幕')
    out.mkdir(parents=True)
    write_json(out/'transcript.json', {'language': info.language, 'segments': cues, 'words': words})
    srt_write(out/'source.srt', cues)
    return {'output': str(out.resolve()), 'segments': len(cues), 'review': '转录未经人工校对；请用 words 拆字幕'}


def split_captions(transcript, limit=16):
    words = transcript.get('words', [])
    if not words:
        raise ValueError('没有词级时间码；不能伪造精确拆句，请使用原句字幕或重新转录')
    cues, group = [], []
    def flush():
        if group:
            cues.append({'start': group[0]['start'], 'end': group[-1]['end'],
                         'text': ''.join(x['text'] for x in group).strip()})
            group.clear()
    for word in words:
        if group and (len(''.join(x['text'] for x in group)+word['text']) > limit
                      or word['start']-group[-1]['end'] > 0.5):
            flush()
        if word['end'] > word['start'] and word['text'].strip():
            group.append(word)
        if re.search(r'[。！？!?；;]$', word['text'].strip()):
            flush()
    flush()
    return cues


def main():
    p = argparse.ArgumentParser(description='WorkBuddy 本地短视频工具')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('doctor')
    q = sub.add_parser('probe'); q.add_argument('source')
    q = sub.add_parser('silence'); q.add_argument('source'); q.add_argument('--out', required=True)
    q.add_argument('--threshold', type=float, default=-35); q.add_argument('--minimum', type=float, default=0.6)
    q.add_argument('--padding', type=float, default=0.15)
    q = sub.add_parser('transcribe'); q.add_argument('source'); q.add_argument('--out', required=True)
    q.add_argument('--model', default='small'); q.add_argument('--allow-model-download', action='store_true')
    q.add_argument('--beam-size', type=int, choices=[1, 5], default=1)
    q.add_argument('--glossary', help='最多 200 字术语提示，不是替换规则')
    q = sub.add_parser('captions'); q.add_argument('transcript'); q.add_argument('--out', required=True)
    q.add_argument('--max-chars', type=int, default=16, choices=range(8, 25))
    q = sub.add_parser('validate'); q.add_argument('manifest')
    q = sub.add_parser('render'); q.add_argument('manifest'); q.add_argument('--out', required=True)
    q = sub.add_parser('restyle'); q.add_argument('previous'); q.add_argument('subtitles'); q.add_argument('--out',required=True)
    q.add_argument('--preset',choices=SUBTITLE_PRESETS); q.add_argument('--font-size',type=float)
    q = sub.add_parser('quality'); q.add_argument('source'); q.add_argument('--out', required=True)
    args = p.parse_args()
    try:
        if args.cmd == 'doctor': result = doctor()
        elif args.cmd == 'probe': result = probe(local_file(args.source, Path.cwd()))
        elif args.cmd == 'silence':
            if Path(args.out).exists(): raise ValueError('输出已存在，请使用新文件名')
            if not (-100 <= args.threshold <= 0 and 0.1 <= args.minimum <= 10 and 0 <= args.padding <= 1):
                raise ValueError('静音参数超出支持范围')
            result = silence_keep(local_file(args.source, Path.cwd()), args.threshold, args.minimum, args.padding)
            write_json(args.out, result)
        elif args.cmd == 'transcribe':
            if args.glossary and len(args.glossary) > 200: raise ValueError('术语提示最多 200 字')
            result = transcribe(local_file(args.source, Path.cwd()), args.out, args.model,
                                args.allow_model_download, args.beam_size, args.glossary)
        elif args.cmd == 'captions':
            if Path(args.out).exists(): raise ValueError('字幕输出已存在，请用新文件名')
            cues = split_captions(read_json(args.transcript), args.max_chars)
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            srt_write(args.out, cues)
            result = {'output': str(Path(args.out).resolve()), 'cues': len(cues), 'timing': 'source'}
        elif args.cmd == 'validate':
            m = validate(args.manifest)
            result = {'valid': True, 'duration': m['duration'], 'clips': len(m['clips']), 'subtitles': len(m['cues'])}
        elif args.cmd == 'render': result = render(args.manifest, args.out)
        elif args.cmd == 'restyle': result = restyle(args.previous,args.subtitles,args.out,args.preset,args.font_size)
        else: result = quality(local_file(args.source, Path.cwd()), args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if (args.cmd in ['render','restyle'] and not result['quality']['machine_pass']) or (args.cmd == 'quality' and not result['machine_pass']):
            return 1
        return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError) as e:
        print(json.dumps({'error': str(e), 'next': '修复所列问题后重试；不要宣称已经出片'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
