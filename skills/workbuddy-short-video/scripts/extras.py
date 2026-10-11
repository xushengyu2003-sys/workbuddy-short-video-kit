#!/usr/bin/env python3
"""Optional local B-roll and simple animated title cards over a receipted base."""
import argparse
import json
from pathlib import Path
import tempfile
import time
import shutil
import video as v


def validate(plan, duration):
    data = v.read_json(plan)
    items = data.get('items', [])
    if not items or len(items) > 30:
        raise ValueError('装饰需要1–30项；未选择装饰时不要调用')
    result = []
    for item in items:
        x = dict(item)
        x['start'] = v.number(x['start'], 'start')
        x['end'] = v.number(x['end'], 'end')
        if x['end'] <= x['start'] or x['end'] > duration:
            raise ValueError('装饰时间必须在成片范围内，使用成片时间')
        if x.get('kind') == 'broll':
            x['source'] = str(v.local_file(x['source'], Path(plan).resolve().parent))
            x['media'] = x.get('media', 'video')
            if x['media'] not in ['image', 'video']:
                raise ValueError('B-roll media只能是image或video')
            x['source_start'] = v.number(x.get('source_start', 0), 'source_start')
            if x['media'] == 'video':
                meta = v.probe(x['source'])
                if not meta['video'] or x['source_start'] + x['end']-x['start'] > meta['duration'] + .04:
                    raise ValueError('B-roll无画面或长度不足')
            x['source_sha256'] = v.file_hash(x['source'])
        elif x.get('kind') == 'title':
            if not isinstance(x.get('text'), str) or not x['text'].strip() or len(x['text']) > 80:
                raise ValueError('MG标题需1–80字；不支持复杂动画')
            if len(x['text'].splitlines()) > 2:
                raise ValueError('MG标题最多两行')
        else:
            raise ValueError('kind只能为broll或title')
        result.append(x)
    # Deterministic stacking: B-roll first, titles on top regardless of JSON ordering.
    return sorted(result, key=lambda x: x['kind'] == 'title')


def decorate(previous, plan, out):
    started = time.perf_counter()
    previous = Path(previous).resolve(); out = Path(out).resolve()
    if previous == out or out.exists():
        raise ValueError('请使用新的输出目录，保留上版')
    receipt = v.read_json(previous/'base.json'); manifest = v.read_json(previous/'edit-plan.json')
    if receipt.get('role') != 'caption_free_mixed_base' or receipt.get('sha256') != v.file_hash(previous/'base.mp4') or receipt.get('plan_sha256') != v.file_hash(previous/'edit-plan.json'):
        raise ValueError('底片或计划校验失败，不能添加装饰')
    # Full decode/probe of user video was already done by render; only inspect base metadata here.
    v.probe(previous/'base.mp4')
    duration = manifest['duration']; w = manifest['width']; h = manifest['height']; fps = manifest['fps']
    items = validate(plan, duration)
    font = v.find_font(manifest.get('font')) if any(x['kind'] == 'title' for x in items) else None
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='wb-extras-') as temp:
        args = [v.tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(previous/'base.mp4')]
        graph = []; last = '[0:v]'
        for i, x in enumerate(items, 1):
            d = x['end']-x['start']; start = x['start']
            if x['kind'] == 'title':
                img = v.subtitle_png(x['text'], w, h, font, {'preset':'accent', 'font_size':72, 'position_y':0.18})
                from PIL import Image
                import io
                # subtitle_png returns PNG bytes; crop transparent area to lower overlay work.
                im = Image.open(io.BytesIO(img)).convert('RGBA'); box = im.getbbox()
                card = Path(temp)/f'title{i}.png'; im.crop((0,box[1],w,box[3])).save(card)
                args += ['-loop','1','-framerate',str(fps),'-t',str(d),'-i',str(card)]
                fade = min(.3,d/3)
                graph.append(f'[{i}:v]format=rgba,fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={d-fade}:d={fade}:alpha=1,setpts=PTS-STARTPTS+{start}/TB[o{i}]')
                y = f'{box[1]}+24*max(0,1-(t-{start})/{fade})'
            else:
                if x['media'] == 'image':
                    args += ['-loop','1','-framerate',str(fps),'-t',str(d),'-i',x['source']]
                else:
                    args += ['-ss',str(x['source_start']),'-t',str(d),'-i',x['source']]
                graph.append(f'[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101820,setsar=1,fps={fps},setpts=PTS-STARTPTS+{start}/TB[o{i}]')
                y = '0'
            graph.append(f"{last}[o{i}]overlay=x=0:y='{y}':enable='gte(t,{start})*lt(t,{x['end']})':eof_action=pass:repeatlast=0[v{i}]")
            last = f'[v{i}]'
        args += ['-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map',last,'-map','0:a:0?',*v.h264_options(manifest),'-c:a','copy','-t',str(duration),'-movflags','+faststart',out/'base.mp4']
        v.run(args)
    visual_seconds = time.perf_counter()-started
    cues = v.srt_read(previous/'subtitles.srt') if (previous/'subtitles.srt').is_file() else []
    manifest['visual_extras'] = items; manifest['cues'] = cues
    if cues:
        v.srt_write(out/'subtitles.srt', cues)
    if cues and manifest.get('burn_subtitles', True):
        v.burn_captions(out/'base.mp4', out/'final.mp4', manifest)
    else:
        shutil.copy2(out/'base.mp4', out/'final.mp4')
    v.write_json(out/'edit-plan.json', {k:x for k,x in manifest.items() if k != 'cues'})
    v.write_json(out/'base.json', {'role':'caption_free_mixed_base','sha256':v.file_hash(out/'base.mp4'),'plan_sha256':v.file_hash(out/'edit-plan.json')})
    report = v.quality(out/'final.mp4',out/'review',expected=duration,width=w,height=h)
    v.write_json(out/'quality.json',report)
    v.write_json(out/'timings.json',{'visual_extras_seconds':round(visual_seconds,3),'total_seconds':round(time.perf_counter()-started,3),'reused_cut_and_mix':True})
    return {'output':str(out/'final.mp4'),'quality':report}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('previous'); p.add_argument('plan'); p.add_argument('--out', required=True)
    a = p.parse_args()
    print(json.dumps(decorate(a.previous,a.plan,a.out),ensure_ascii=False,indent=2))
