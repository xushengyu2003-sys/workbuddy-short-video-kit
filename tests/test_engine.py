import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('video', ROOT/'skills/workbuddy-short-video/scripts/video.py')
video = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video)


class EditingTests(unittest.TestCase):
    def test_timestamp_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'字幕.srt'
            cues = [{'start': 59.9996, 'end': 3601.234, 'text': '中文\n第二行'}]
            video.srt_write(p, cues)
            actual = video.srt_read(p)
            self.assertEqual(actual[0]['start'], 60)
            self.assertEqual(actual[0]['text'], cues[0]['text'])

    def test_reordered_source_captions(self):
        cues = [{'start': 1, 'end': 2, 'text': '甲'}, {'start': 5, 'end': 6, 'text': '乙'}]
        result = video.remap(cues, [{'start': 4, 'end': 7}, {'start': 0, 'end': 3}])
        self.assertEqual([(x['start'], x['text']) for x in result], [(1, '乙'), (4, '甲')])

    def test_nonfinite_rejected(self):
        for value in [float('nan'), float('inf'), -1, True]:
            with self.assertRaises(ValueError): video.number(value, 'start')

    def test_network_input_rejected(self):
        with self.assertRaises(ValueError): video.local_file('https://example.com/a.mp4', ROOT)

    def test_word_captions_preserve_timing(self):
        words = [{'start': 1, 'end': 2, 'text': '完整观点。'},
                 {'start': 3, 'end': 4, 'text': '后一句'}]
        actual = video.split_captions({'words': words})
        self.assertEqual([(c['start'],c['end']) for c in actual], [(1,2),(3,4)])
        with self.assertRaises(ValueError): video.split_captions({'segments': []})

    def test_caption_layout_rejected(self):
        with self.assertRaises(ValueError):
            video.subtitle_png('文字'*100, 360, 640, video.find_font())


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='wb-test-')
        cls.base = Path(cls.temp.name)
        cls.source = cls.base/'中文 空格 $素材.mp4'
        video.run([video.tool('ffmpeg'), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                   'testsrc2=size=320x240:rate=30:duration=3', '-f', 'lavfi', '-i',
                   "aevalsrc=if(between(t\\,1\\,2)\\,0\\,0.2*sin(2*PI*440*t)):s=48000:d=3",
                   '-c:v', 'libx264', '-c:a', 'aac', '-shortest', cls.source])

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def plan(self):
        return {'schema_version': 1, 'width': 360, 'height': 640, 'fps': 30,
                'clips': [{'source': str(self.source), 'start': 0, 'end': 0.9},
                          {'source': str(self.source), 'start': 2.1, 'end': 3}]}

    def save(self, m, name):
        p = self.base/name
        video.write_json(p, m)
        return p

    def test_silence_detects_gap(self):
        result = video.silence_keep(self.source)
        self.assertEqual(len(result['keep']), 2)
        self.assertLess(sum(c['end']-c['start'] for c in result['keep']), 2.5)

    def test_reject_out_of_bounds(self):
        m = self.plan(); m['clips'][0]['end'] = 100
        with self.assertRaises(ValueError): video.validate(self.save(m, 'bounds.json'))

    def test_reject_multisource_source_subtitles(self):
        other = self.base/'other.mp4'; other.write_bytes(self.source.read_bytes())
        srt = self.base/'multi.srt'; video.srt_write(srt, [{'start': 0, 'end': 0.5, 'text': '字幕'}])
        m = self.plan(); m['clips'][1]['source'] = str(other)
        m.update(subtitles=str(srt), subtitle_timing='source')
        with self.assertRaises(ValueError): video.validate(self.save(m, 'multi.json'))

    def test_render_captions_and_preserve_source(self):
        original = self.source.read_bytes()
        srt = self.base/'source.srt'
        video.srt_write(srt, [{'start': 0.1, 'end': 0.8, 'text': '保留完整观点'},
                              {'start': 2.2, 'end': 2.8, 'text': '自动剪辑与字幕'}])
        m = self.plan(); m.update(subtitles=str(srt), subtitle_timing='source')
        p = self.save(m, 'render.json'); out = self.base/'render'
        result = video.render(p, out)
        self.assertTrue(result['quality']['machine_pass'])
        self.assertEqual(self.source.read_bytes(), original)
        self.assertAlmostEqual(video.srt_read(out/'subtitles.srt')[1]['start'], 1.0)
        self.assertEqual(len(list((out/'review').glob('*.jpg'))), 3)
        with self.assertRaises(ValueError): video.render(p, out)

    def test_mixed_image_video_with_music(self):
        from PIL import Image
        img = self.base/'slide.png'; Image.new('RGB', (360, 640), '#203550').save(img)
        m = self.plan(); m['clips'][1] = {'source': str(img), 'kind': 'image', 'start': 0, 'end': 0.9}
        m['music'] = str(self.source)
        result = video.render(self.save(m, 'mixed.json'), self.base/'mixed')
        self.assertTrue(result['quality']['machine_pass'])

    def test_reject_bad_subtitle_timeline(self):
        srt = self.base/'bad.srt'; video.srt_write(srt, [{'start': 0, 'end': 99, 'text': '越界'}])
        m = self.plan(); m['subtitles'] = str(srt)
        with self.assertRaises(ValueError): video.validate(self.save(m, 'bad.json'))


if __name__ == '__main__': unittest.main(verbosity=2)
