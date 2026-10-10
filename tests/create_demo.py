"""Create original synthetic speech fixture on macOS; no private footage."""
import importlib.util
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('video', ROOT/'skills/workbuddy-short-video/scripts/video.py')
video = importlib.util.module_from_spec(spec); spec.loader.exec_module(video)
d = ROOT/'demo'; d.mkdir(exist_ok=True)
phrases = ['剪短视频，先保留完整的观点。', '再删除多余停顿，添加清楚的字幕。', '最后检查画面和声音，再交付成片。']
im = Image.new('RGB', (720,1280), '#111e2d'); draw = ImageDraw.Draw(im)
font = video.find_font()
def text(x,y,s,size,color): draw.text((x,y), s, font=ImageFont.truetype(font,size), fill=color)
text(64,95,'WORKBUDDY',34,'#51d6ba')
text(64,178,'短视频剪辑',64,'white'); text(64,265,'本地执行 · 中文字幕',32,'#abc0d0')
draw.rounded_rectangle((64,390,656,835), radius=30, fill='#203448')
for i, s in enumerate(['保留完整观点','删除多余停顿','字幕跟随声音']):
    text(100,446+i*115,f'0{i+1}',30,'#51d6ba'); text(173,440+i*115,s,38,'white')
text(64,1140,'合成语音测试素材 · 非真人口播',24,'#abc0d0')
im.save(d/'demo-card.png')
parts, cues, cursor = [], [], 0.0
for i, phrase in enumerate(phrases):
    a = d/f'voice-{i}.aiff'
    video.run(['/usr/bin/say','-v','Tingting','-r','190','-o',a,phrase])
    dur = video.probe(a)['duration']
    cues.append({'start':cursor,'end':cursor+dur,'text':phrase})
    out = d/f'speech-{i}.mp4'
    video.run([video.tool('ffmpeg'),'-v','error','-y','-loop','1','-i',d/'demo-card.png',
               '-i',a,'-t',str(dur+1),'-vf','fps=30,format=yuv420p','-af','apad',
               '-c:v','libx264','-preset','fast','-c:a','aac','-ar','48000','-ac','2',out])
    parts.append(out.name); cursor += dur+1
(d/'list.txt').write_text(''.join("file '"+x+"'\n" for x in parts))
video.run([video.tool('ffmpeg'),'-v','error','-y','-f','concat','-safe','1','-i','list.txt',
           '-c','copy',d/'input.mp4'],cwd=d)
video.srt_write(d/'known-source.srt',cues)
video.write_json(d/'fixture.json',{'phrases':phrases,'cues':cues,'source_duration':cursor,
                                 'description':'Original card plus macOS system synthetic voice; known phrase-level timings, not ASR output.'})
print(d/'input.mp4')
