import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/workbuddy-short-video/scripts'))
import extras
import video as v

class ExtrasTests(unittest.TestCase):
    def test_preserve_audio_visual_window_and_restyle_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            v.run([v.tool('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=blue:s=320x480:r=10:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',p/'source.mp4'])
            from PIL import Image
            Image.new('RGB',(320,480),'red').save(p/'red.png')
            v.write_json(p/'plan.json',{'schema_version':1,'width':320,'height':480,'fps':10,'clips':[{'source':str(p/'source.mp4'),'start':0,'end':2}],'burn_subtitles':False})
            v.render(p/'plan.json',p/'original')
            v.write_json(p/'extras.json',{'items':[{'kind':'title','text':'重点观点','start':.2,'end':1.8},{'kind':'broll','media':'image','source':'red.png','start':.6,'end':1.4}]})
            result=extras.decorate(p/'original',p/'extras.json',p/'decorated')
            self.assertTrue(result['quality']['machine_pass'])
            # Audio packet data remains byte-identical through optional visuals.
            def audio(path):
                return v.run([v.tool('ffmpeg'),'-v','error','-i',path,'-map','0:a:0','-c','copy','-f','adts','pipe:1'],binary=True).stdout
            self.assertEqual(audio(p/'original/base.mp4'),audio(p/'decorated/base.mp4'))
            def pixel(t):
                raw=v.run([v.tool('ffmpeg'),'-v','error','-ss',str(t),'-i',p/'decorated/final.mp4','-frames:v','1','-vf','crop=2:2:160:400','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],binary=True)
                return tuple(raw.stdout[:3])
            self.assertGreater(pixel(.1)[2],200)
            self.assertGreater(pixel(1)[0],200)
            self.assertGreater(pixel(1.8)[2],200)
            def frame(t):
                return v.run([v.tool('ffmpeg'),'-v','error','-ss',str(t),'-i',p/'decorated/final.mp4','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],binary=True).stdout
            self.assertNotEqual(frame(1.6),frame(1.9))  # title visible outside B-roll window
            v.srt_write(p/'new.srt',[{'start':0,'end':2,'text':'字幕仍可修改'}])
            self.assertTrue(v.restyle(p/'decorated',p/'new.srt',p/'restyled')['quality']['machine_pass'])
    def test_bounds_and_invalid_type(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'
            for item in [{'kind':'title','text':'标题','start':0,'end':3},{'kind':'unknown','start':0,'end':1}]:
                v.write_json(p,{'items':[item]})
                with self.assertRaises(ValueError): extras.validate(p,2)
if __name__=='__main__': unittest.main()
