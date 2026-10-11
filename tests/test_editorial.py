import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
import test_engine

SCRIPTS=test_engine.ROOT/'skills/workbuddy-short-video/scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('editorial',SCRIPTS/'editorial.py')
editorial=importlib.util.module_from_spec(spec);spec.loader.exec_module(editorial)
video=editorial.video

class FineEditingTests(unittest.TestCase):
    def test_phrase_captions_use_output_axis_and_full_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);retained=base/'words.json';phrases=base/'phrases.json'
            video.write_json(retained,{'timing':'output','duration':3,'words':[
                {'word_id':10,'start':0.1,'end':0.8,'source_start':20,'source_end':20.7,'text':'信息'},
                {'word_id':12,'start':0.8,'end':1.5,'source_start':30,'source_end':30.7,'text':'完整'}]})
            video.write_json(phrases,{'phrases':[{'first_word_id':10,'last_word_id':12,'text':'信息完整'}]})
            result=editorial.phrase_captions(retained,phrases,base/'good.srt')
            cue=video.srt_read(base/'good.srt')[0]
            self.assertEqual((cue['start'],cue['end']),(0.1,1.5));self.assertEqual(result['warnings'],[])
            video.write_json(phrases,{'phrases':[{'first_word_id':10,'last_word_id':10,'text':'信息'}]})
            with self.assertRaises(ValueError): editorial.phrase_captions(retained,phrases,base/'missing.srt')
            self.assertFalse((base/'missing.srt').exists())
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='wb-fine-');cls.base=Path(cls.temp.name);cls.source=cls.base/'source.mp4'
        video.run([video.tool('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=size=320x240:rate=30:duration=3',
                   '-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-c:a','aac','-shortest',cls.source])
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def proposals(self, name, extra=None):
        words=extra or [{'start':.1,'end':.4,'text':'这个'},{'start':.4,'end':.7,'text':'这个'},
                       {'start':.8,'end':1.2,'text':'观点'},{'start':2,'end':2.3,'text':'结论'}]
        trans=self.base/(name+'-trans.json');video.write_json(trans,{'words':words})
        p=editorial.analyze(self.source,trans);path=self.base/(name+'-prop.json');video.write_json(path,p);return path,p
    def decisions(self,name,items):
        path=self.base/(name+'-dec.json');video.write_json(path,items);return path
    def test_deleted_words_leave_audio_plan_and_captions(self):
        path,p=self.proposals('delete');c=next(c for c in p['candidates'] if c['kind']=='repetition')
        d=self.decisions('delete',{'decisions':[{'id':c['id'],'action':'delete','reason':'重复','evidence':'相邻原文'}]})
        out=self.base/'delete';result=editorial.compile_plan(path,d,out)
        self.assertAlmostEqual(result['duration'],p['duration']-.3)
        text=''.join(c['text'] for c in video.srt_read(out/'subtitles.srt'));self.assertEqual(text.count('这个'),1)
        self.assertIn('观点',text);self.assertIn('结论',text)
        m=video.validate(out/'edit-plan.json');self.assertEqual(m['subtitle_timing'],'output')
        self.assertEqual(m['subtitle_style']['preset'],'readable')
        # Verify actual media uses the compiled timeline and new caption style.
        m['width']=360;m['height']=640;video.write_json(out/'small-plan.json',{k:v for k,v in m.items() if k!='cues'})
        render=video.render(out/'small-plan.json',self.base/'delete-render');self.assertTrue(render['quality']['machine_pass'])
    def test_caption_phrase_survives_internal_cut(self):
        words=[{'start':.1,'end':.4,'text':'面向'}, {'start':.4,'end':.7,'text':'这个'},
               {'start':.7,'end':1.,'text':'这个'}, {'start':1.,'end':1.3,'text':'用户'}]
        path,p=self.proposals('phrase',words)
        c=next(c for c in p['candidates'] if c['kind']=='repetition')
        d=self.decisions('phrase',{'decisions':[{'id':c['id'],'action':'delete','reason':'重复','evidence':'相邻原文'}]})
        out=self.base/'phrase';editorial.compile_plan(path,d,out)
        cues=video.srt_read(out/'subtitles.srt')
        self.assertEqual(len(cues),1);self.assertEqual(cues[0]['text'],'面向这个用户')
        self.assertEqual(cues[0]['start'],.1);self.assertAlmostEqual(cues[0]['end'],1.)
        audit=video.read_json(out/'cut-report.json')['audit'];self.assertTrue(all(c['decision']!='pending' for c in audit))

    def test_undecided_stays_in_output(self):
        path,p=self.proposals('keep');d=self.decisions('keep',{});out=self.base/'keep';r=editorial.compile_plan(path,d,out)
        self.assertEqual(r['duration'],p['duration']);self.assertEqual(r['pending_kept'],len(p['candidates']))
    def test_single_character_reduplication_not_stutter(self):
        _,p=self.proposals('daily',[{'start':.1,'end':.2,'text':'天'},{'start':.2,'end':.3,'text':'天'},{'start':.3,'end':.5,'text':'学习'}])
        self.assertFalse(any(c['kind']=='repetition' for c in p['candidates']))
    def test_partial_word_delete_rejected(self):
        path,p=self.proposals('partial');p['candidates'].append({'id':'bad','kind':'pause','start':.85,'end':1.1,'word_ids':[]})
        video.write_json(path,p);d=self.decisions('partial',{'decisions':[{'id':'bad','action':'delete','reason':'测试','evidence':'测试'}]})
        with self.assertRaises(ValueError):editorial.compile_plan(path,d,self.base/'partial')
    def test_transcript_drift_rejected(self):
        path,p=self.proposals('drift');Path(p['transcript']).write_text('{"words":[]}');d=self.decisions('drift',{})
        with self.assertRaises(ValueError):editorial.compile_plan(path,d,self.base/'drift')
    def test_zero_duration_text_retained_without_fake_time(self):
        words=[{'start':.1,'end':.3,'text':'完整'},{'start':.3,'end':.3,'text':'这个'},{'start':.3,'end':.7,'text':'观点'}]
        path,p=self.proposals('zero',words);self.assertEqual(p['timing_warnings'],[1])
        out=self.base/'zero';editorial.compile_plan(path,self.decisions('zero',{}),out)
        self.assertIn('这个',''.join(c['text'] for c in video.srt_read(out/'subtitles.srt')))
        bad={'manual_cuts':[{'word_ids':[0],'reason':'测试','evidence':'测试'}]}
        with self.assertRaises(ValueError):editorial.compile_plan(path,self.decisions('zero-bad',bad),self.base/'zero-bad')
    def test_measured_pause_does_not_cut_words(self):
        _,p=self.proposals('measured');trans=Path(p['transcript']);sil=self.base/'sil.json'
        video.write_json(sil,{'source':str(self.source),'duration':p['duration'],'silences':[{'start':1.3,'end':1.9}]})
        p=editorial.analyze(self.source,trans,silence_path=sil)
        c=next(c for c in p['candidates'] if c['kind']=='pause' and c['risk']=='medium')
        self.assertGreaterEqual(c['start'],1.3);self.assertLessEqual(c['end'],1.9)
    def test_styles_change_pixels_and_validate(self):
        font=video.find_font();a=Image.open(io.BytesIO(video.subtitle_png('清晰字幕',1080,1920,font,{'preset':'classic'})))
        b=Image.open(io.BytesIO(video.subtitle_png('清晰字幕',1080,1920,font,{'preset':'readable'})))
        self.assertGreater(b.getbbox()[2]-b.getbbox()[0],a.getbbox()[2]-a.getbbox()[0])
        for style in [{'font_size':999},{'position_y':float('nan')},{'color':'red'},{'unknown':1},[],{'preset':'fake'}]:
            with self.assertRaises(ValueError):video.subtitle_style(style)
    def test_zero_duration_and_overlap_handled(self):
        with self.assertRaises(ValueError):editorial.checked_words({'words':[{'start':0,'end':1,'text':'甲'},{'start':.5,'end':2,'text':'乙'}]},3)
    def test_manual_semantic_cut_requires_evidence(self):
        path,_=self.proposals('reason');d=self.decisions('reason',{'manual_cuts':[{'word_ids':[0],'reason':'删除'}]})
        with self.assertRaises(ValueError):editorial.compile_plan(path,d,self.base/'reason')

if __name__=='__main__':unittest.main(verbosity=2)
