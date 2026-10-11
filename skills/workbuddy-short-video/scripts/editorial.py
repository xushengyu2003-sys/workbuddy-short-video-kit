#!/usr/bin/env python3
"""Local cut proposals, word-grounded compilation and subtitle style previews.
Original implementation; proposals require editorial decisions, never imply listening.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import video

MODES = {'light': (0.8, 0.2), 'tight': (0.4, 0.12), 'highlight': (0.4, 0.12)}
FILLERS = {'嗯', '呃', '额', '啊', '这个', '那个', '然后', '就是', '对吧'}


def fingerprint(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def checked_words(transcript, duration):
    words = []
    for i, original in enumerate(transcript.get('words', [])):
        w = dict(original)
        w['start'] = video.number(w['start'], 'word.start')
        w['end'] = video.number(w['end'], 'word.end')
        if w['end'] < w['start'] or w['end'] > duration + 0.05:
            raise ValueError('无效词时间；请先修复转录')
        if words and w['start'] < words[-1]['end'] - 0.001:
            raise ValueError('词时间重叠；请先对齐或修复转录，不能据此精剪')
        if not isinstance(w.get('text'), str) or not w['text'].strip():
            raise ValueError('词文本为空')
        w['word_id'] = i
        if w['end'] == w['start']: w['timing_issue'] = 'zero_duration'
        words.append(w)
    if not words: raise ValueError('精剪需要真实词级时间轴')
    return words


def clean(text):
    return re.sub(r'[\s，。！？、；：,.!?;:]', '', text)


def analyze(source, transcript_path, mode='tight', silence_path=None):
    source = video.local_file(source, Path.cwd())
    duration = video.probe(source)['duration']
    words = checked_words(video.read_json(transcript_path), duration)
    minimum, pad = MODES[mode]; candidates = []
    def add(kind, start, end, ids, risk, note):
        if end-start < 0.04: return
        i = ids[0] if ids else next((j for j,w in enumerate(words) if w['start'] >= end), len(words))
        context = ''.join(w['text'] for w in words[max(0,i-5):min(len(words),i+8)])
        candidates.append({'id': 'c%04d' % (len(candidates)+1), 'kind': kind,
                           'start': round(start,6), 'end': round(end,6), 'word_ids': ids,
                           'text': ''.join(words[j]['text'] for j in ids), 'context': context,
                           'risk': risk, 'note': note, 'decision': 'pending'})
    silences = []
    if silence_path:
        data = video.read_json(silence_path)
        if Path(data['source']).resolve() != source or abs(data['duration']-duration) > 0.1:
            raise ValueError('静音报告不属于当前素材')
        silences = data.get('silences', [])
    gaps = [(0, words[0]['start'])] + [(a['end'],b['start']) for a,b in zip(words,words[1:])] + [(words[-1]['end'],duration)]
    for a,b in gaps:
        if b-a < minimum: continue
        lo,hi = a+pad,b-pad
        measured = [(max(lo,s['start']+0.03), min(hi,s['end']-0.03)) for s in silences]
        measured = [(x,y) for x,y in measured if y-x >= 0.1]
        if measured:
            for x,y in measured: add('pause', x,y,[], 'medium', '音量静音与词间空隙交集；仍可能包含呼吸或漏识别轻声')
        else: add('pause',lo,hi,[], 'high', '只有 ASR 空隙证据；无词不等于无声音，需听音确认')
    for i,w in enumerate(words):
        t = clean(w['text'])
        if t in FILLERS and mode != 'light' and w['end'] > w['start']:
            add('filler',w['start'],w['end'],[i],'high','上下文判断；这个/然后/就是等可能承担指代或逻辑，不可按词表盲删')
        if i+1 < len(words) and len(t) >= 2 and t == clean(words[i+1]['text']) and words[i+1]['start']-w['end'] <= 0.4:
            add('repetition',w['start'],w['end'],[i],'medium','相邻重复候选，默认保后；可能是强调，须读上下文')
    return {'schema_version':1,'source':str(source),'duration':duration,'source_sha256':fingerprint(source),
            'transcript':str(Path(transcript_path).resolve()),'transcript_sha256':fingerprint(transcript_path),
            'mode':mode,'minimum_gap':minimum,'padding':pad,'words':words,'candidates':candidates,
            'timing_warnings':[w['word_id'] for w in words if w.get('timing_issue')],
            'semantic_review':'pending: 改口、重复解释、跑题和逻辑结构由宿主逐轮阅读判断；脚本不推断完整观点'}


def caption_units(words):
    # Fold untimed text into an adjacent timed unit. Do not invent token timestamps.
    result=[];pending=''
    for word in words:
        if word['end']==word['start']:
            pending+=word['text'];continue
        unit=dict(word,text=pending+word['text']);pending='';result.append(unit)
    if pending:
        if not result: raise ValueError('该片段只有零时长词，需重新对齐')
        result[-1]['text']+=pending
    return result


def compile_plan(proposals, decisions, out):
    p = video.read_json(proposals); d = video.read_json(decisions)
    source = video.local_file(p['source'], Path.cwd())
    if fingerprint(source) != p['source_sha256'] or fingerprint(p['transcript']) != p['transcript_sha256']:
        raise ValueError('素材或转录已改变，请重新生成候选')
    words = checked_words(video.read_json(p['transcript']),p['duration'])
    if words != p['words']: raise ValueError('候选词时间轴已改变')
    candidates = {c['id']:c for c in p['candidates']}; cuts=[]; audit=[]; seen=set()
    for item in d.get('decisions',[]):
        cid=item['id']
        if cid not in candidates or cid in seen: raise ValueError('未知或重复候选编号')
        seen.add(cid)
        if item['action'] not in ['keep','delete']: raise ValueError('决定必须 keep/delete')
        if not item.get('reason'): raise ValueError('每个决定需要原因')
        c=candidates[cid]
        if item['action']=='delete':
            if not item.get('evidence'): raise ValueError('删除需要上下文/音频证据说明')
            cuts.append((c['start'],c['end']))
        audit.append(dict(c, **{'action':item['action'],'decision':item['action'],'reason':item['reason'],'evidence':item.get('evidence','')}))
    for item in d.get('manual_cuts',[]):
        ids=item['word_ids']
        if not ids or any(type(i) is not int for i in ids) or ids != list(range(ids[0],ids[-1]+1)) or ids[0]<0 or ids[-1]>=len(words):
            raise ValueError('手工语义删除须为连续有效 word_ids，不能猜字级时间')
        if not item.get('reason') or not item.get('evidence'): raise ValueError('语义删除需要理由与证据')
        cuts.append((words[ids[0]]['start'],words[ids[-1]]['end']))
        audit.append(dict(item,kind='semantic',action='delete'))
    merged=[]
    for a,b in sorted(cuts):
        if merged and a <= merged[-1][1]+0.000001: merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else: merged.append((a,b))
    for w in words:
        for a,b in merged:
            if w.get('timing_issue') and a-0.08 <= w['start'] <= b+0.08:
                raise ValueError('删除靠近零时长词，需要先重新对齐：'+w['text'])
            if min(w['end'],b)-max(w['start'],a) > 0.000001 and not (a <= w['start']+0.000001 and b >= w['end']-0.000001):
                raise ValueError('删除切进了保留词：'+w['text'])
    clips=[];cursor=0
    for a,b in merged:
        if a>cursor+0.000001: clips.append({'source':str(source),'start':cursor,'end':a})
        cursor=b
    if p['duration']>cursor+0.000001: clips.append({'source':str(source),'start':cursor,'end':p['duration']})
    if not clips: raise ValueError('不能删除整个视频')
    # Map surviving words before regrouping. A caption may bridge a cut, but never retains deleted text.
    cues=[];offset=0;retained=[];caption_words=[]
    for c in clips:
        part=[]
        for w in words:
            if w['start'] >= c['start']-0.000001 and w['end'] <= c['end']+0.000001:
                mapped=dict(w,source_start=w['start'],source_end=w['end'],
                            start=w['start']-c['start']+offset,end=w['end']-c['start']+offset)
                part.append(mapped);retained.append(mapped)
        caption_words.extend(caption_units(part) if part else [])
        offset+=c['end']-c['start']
    cues=video.split_captions({'words':caption_words},limit=12) if caption_words else []
    out=Path(out)
    if out.exists(): raise ValueError('编译输出已存在，请使用新目录')
    out.mkdir(parents=True)
    video.srt_write(out/'subtitles.srt',cues)
    manifest={'schema_version':1,'width':1080,'height':1920,'fps':30,'clips':clips,'subtitles':'subtitles.srt',
              'subtitle_timing':'output','burn_subtitles':True,'subtitle_style':{'preset':'readable'}}
    video.write_json(out/'edit-plan.json',manifest)
    video.write_json(out/'retained-words.json',{'timing':'output','duration':offset,'source':str(source),'words':retained})
    joins=[];offset=0
    for left,right in zip(clips,clips[1:]):
        offset+=left['end']-left['start']
        joins.append({'output_time':offset,'left_source_end':left['end'],'right_source_start':right['start'],
                      'listen_window':[max(0,offset-0.8),min(sum(c['end']-c['start'] for c in clips),offset+0.8)]})
    report={'original_duration':p['duration'],'output_duration':sum(c['end']-c['start'] for c in clips),
            'removed_seconds':sum(b-a for a,b in merged),'audit':audit,
            'undecided_kept':sorted(set(candidates)-seen),'joins':joins,'listening_review':'pending',
            'semantic_review':d.get('semantic_review','pending'),'caption_text':'原始 ASR 的保留词；仍需术语校对'}
    video.write_json(out/'cut-report.json',report)
    video.validate(out/'edit-plan.json')
    return {'output':str(out.resolve()),'duration':report['output_duration'],'cuts':len(merged),'pending_kept':len(report['undecided_kept'])}


def phrase_captions(retained_path, phrases_path, out):
    """Host chooses complete phrases; this tool supplies the real output timing and coverage check."""
    data = video.read_json(retained_path)
    if data.get('timing') != 'output': raise ValueError('保留词表必须明确 timing=output；旧文件先用 build 重新编译')
    words = checked_words(data,data['duration']); by_id = {}
    # checked_words validates times but regenerates IDs: restore the stable source IDs explicitly.
    for validated,original in zip(words,data['words']):
        wid = original['word_id']
        if type(wid) is not int or wid in by_id: raise ValueError('重复或无效词 ID')
        by_id[wid] = dict(validated,word_id=wid)
    covered=[];cues=[];warnings=[]
    for p in video.read_json(phrases_path)['phrases']:
        a,b=p['first_word_id'],p['last_word_id']
        if type(a) is not int or type(b) is not int or a>b or a not in by_id or b not in by_id:
            raise ValueError('短语首末词必须为有效保留词 ID')
        ids=[i for i in by_id if a<=i<=b]
        text=p['text'].strip()
        if not text or len(text.splitlines())>2: raise ValueError('短语文本需非空，最多两行')
        start,end=by_id[a]['start'],by_id[b]['end']
        if end<=start or (cues and start<cues[-1]['end']-0.001): raise ValueError('短语时间重叠、倒退或无时长')
        if end-start<0.6: warnings.append({'first_word_id':a,'last_word_id':b,'reason':'短于0.6秒，建议合并完整短语，不延长虚构时间'})
        cues.append({'start':start,'end':end,'text':text}); covered.extend(ids)
    if covered!=list(by_id): raise ValueError('短语必须按顺序覆盖每个保留词一次，不能漏词/重复/调序')
    out=Path(out)
    if out.exists(): raise ValueError('字幕输出已存在')
    out.parent.mkdir(parents=True,exist_ok=True);video.srt_write(out,cues)
    return {'output':str(out.resolve()),'cues':len(cues),'timing':'output','warnings':warnings,
            'text_review':'宿主提供的短语/校对文字，工具只校验时间与覆盖，不证明文字准确'}


def review_table(proposals, out):
    p=video.read_json(proposals); transcript=video.read_json(p['transcript'])
    lines=['# 全文精剪阅读表','词 ID 由程序产生；时间均为素材 source 秒。先读全文再定删留。','',
           '| 词 ID 范围 | 原片时间 | ASR 原文 |','|---|---|---|']
    rows=transcript.get('segments') or [{'start':0,'end':p['duration']}]
    for segment in rows:
        part=[w for w in p['words'] if segment['start']<=w['start']<segment['end']]
        if part:
            text=''.join(w['text'] for w in part).replace('|','／').replace('\n',' ')
            lines.append(f"| {part[0]['word_id']}–{part[-1]['word_id']} | {part[0]['start']:.2f}–{part[-1]['end']:.2f} | {text} |")
    lines += ['', '## 候选（不是自动删词结果）']
    for c in p['candidates']:
        lines.append(f"- {c['id']} / {c['kind']} / {c['start']:.2f}–{c['end']:.2f} / 词{c['word_ids']} / {c['context']}")
    out=Path(out)
    if out.exists(): raise ValueError('阅读表已存在')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'output':str(out.resolve()),'timing':'source'}


def style_preview(source, out, at=20, text='机会还是要自己找', font=None):
    from PIL import Image
    source=video.local_file(source,Path.cwd()); duration=video.probe(source)['duration']
    if not 0 <= at < duration: raise ValueError('预览时间超出素材')
    out=Path(out)
    if out.exists(): raise ValueError('预览目录已存在')
    out.mkdir(parents=True)
    raw=video.run([video.tool('ffmpeg'),'-hide_banner','-loglevel','error','-nostdin','-ss',str(at),'-i',source,
                   '-frames:v','1','-vf','scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
                   '-f','image2pipe','-vcodec','png','pipe:1'],binary=True).stdout
    frame=Image.open(io.BytesIO(raw)).convert('RGBA'); font=video.find_font(font)
    for preset in video.SUBTITLE_PRESETS:
        overlay=Image.open(io.BytesIO(video.subtitle_png(text,1080,1920,font,{'preset':preset})))
        Image.alpha_composite(frame,overlay).convert('RGB').save(out/(preset+'.jpg'),quality=92)
    video.write_json(out/'preview.json',{'source_time':at,'text':text,'presets':video.SUBTITLE_PRESETS,
                                       'note':'同一渲染器的静帧预览；不证明字幕识别或音画同步'})
    return {'output':str(out.resolve()),'presets':list(video.SUBTITLE_PRESETS)}


def main():
    parser=argparse.ArgumentParser(description='口播精剪与样式工具');sub=parser.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('analyze');q.add_argument('source');q.add_argument('transcript');q.add_argument('--mode',choices=MODES,default='tight');q.add_argument('--silence');q.add_argument('--out',required=True)
    q=sub.add_parser('build');q.add_argument('proposals');q.add_argument('decisions');q.add_argument('--out',required=True)
    q=sub.add_parser('captions');q.add_argument('retained');q.add_argument('phrases');q.add_argument('--out',required=True)
    q=sub.add_parser('review');q.add_argument('proposals');q.add_argument('--out',required=True)
    q=sub.add_parser('style-preview');q.add_argument('source');q.add_argument('--out',required=True);q.add_argument('--at',type=float,default=20);q.add_argument('--text',default='机会还是要自己找');q.add_argument('--font')
    args=parser.parse_args()
    try:
        if args.cmd=='analyze':
            if Path(args.out).exists(): raise ValueError('候选输出已存在')
            result=analyze(args.source,args.transcript,args.mode,args.silence);video.write_json(args.out,result)
            result={'output':str(Path(args.out).resolve()),'candidates':len(result['candidates']),'mode':result['mode']}
        elif args.cmd=='build':result=compile_plan(args.proposals,args.decisions,args.out)
        elif args.cmd=='captions':result=phrase_captions(args.retained,args.phrases,args.out)
        elif args.cmd=='review':result=review_table(args.proposals,args.out)
        else:result=style_preview(args.source,args.out,args.at,args.text,args.font)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,ImportError,KeyError,TypeError) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
