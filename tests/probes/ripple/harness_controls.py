#!/usr/bin/env python3
"""CPU/mock refusal controls for ripple artifact provenance; never invokes FFmpeg or a GPU."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import dump
import render
import replay


class HarnessControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ripple-harness-control-')
        self.root=Path(self.temp.name)
        self.source=self.root/'source.mkv';self.source.write_bytes(b'source fixture')
        self.shader=self.root/'shader.glsl';self.shader.write_text('mock shader; never compiled')

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def info(frames=2,rate='24000/1001'):
        return dict(width=2,height=2,r_frame_rate=rate,nb_read_frames=str(frames))

    def test_render_failure_invalidates_old_success_and_preserves_old_video(self):
        out=self.root/'renders';out.mkdir()
        video=out/'linear.mkv';video.write_bytes(b'old complete video')
        record=out/'linear.json';record.write_text('{"execution_status":"complete"}')
        def failure(command,*args):
            Path(command[-1]).write_bytes(b'partial video')
            raise RuntimeError('injected renderer failure')
        argv=['render.py',str(out),str(self.source),'--ffmpeg','never','--ffprobe','never','--shaders','linear=linear']
        with patch('sys.argv',argv),patch.object(render,'probe',return_value=self.info()),patch.object(render,'call',side_effect=failure):
            with self.assertRaisesRegex(RuntimeError,'injected'):
                render.main()
        self.assertEqual(json.loads(record.read_text())['execution_status'],'incomplete')
        self.assertEqual(video.read_bytes(),b'old complete video')
        self.assertEqual((out/'linear.partial.mkv').read_bytes(),b'partial video')

    def test_render_success_commits_media_and_hashes(self):
        out=self.root/'renders'
        def success(command,*args):
            Path(command[-1]).write_bytes(b'new complete video')
            return b'',0.0
        argv=['render.py',str(out),str(self.source),'--ffmpeg','never','--ffprobe','never','--shaders','linear=linear']
        with patch('sys.argv',argv),patch.object(render,'probe',side_effect=[self.info(),self.info(4,'48000/1001')]),patch.object(render,'call',side_effect=success),contextlib.redirect_stdout(io.StringIO()):
            render.main()
        doc=json.loads((out/'linear.json').read_text())
        self.assertEqual(doc['execution_status'],'complete')
        self.assertEqual(doc['source_sha256'],render.sha256(self.source))
        self.assertEqual(doc['output_sha256'],render.sha256(out/'linear.mkv'))
        self.assertFalse((out/'linear.partial.mkv').exists())

    def test_dump_failure_invalidates_old_success_and_preserves_array(self):
        out=self.root/'field.npy';out.write_bytes(b'old array')
        out.with_suffix('.json').write_text('{"execution_status":"complete"}')
        argv=['dump.py',str(out),str(self.source),'--ffmpeg','never','--ffprobe','never','--shader',str(self.shader),'--frames','1']
        with patch('sys.argv',argv),patch.object(dump,'probe',return_value=self.info()),patch.object(dump,'call',side_effect=RuntimeError('injected dump failure')):
            with self.assertRaisesRegex(RuntimeError,'injected'):
                dump.main()
        self.assertEqual(out.read_bytes(),b'old array')
        self.assertEqual(json.loads(out.with_suffix('.json').read_text())['execution_status'],'incomplete')

    def test_dump_success_and_hash_mismatch_refusal(self):
        out=self.root/'field.npy';raw=np.full((1,2,2,3),32768,dtype='<u2').tobytes()
        argv=['dump.py',str(out),str(self.source),'--ffmpeg','never','--ffprobe','never','--shader',str(self.shader),'--frames','1']
        with patch('sys.argv',argv),patch.object(dump,'probe',return_value=self.info()),patch.object(dump,'call',return_value=(raw,0.0)),contextlib.redirect_stdout(io.StringIO()):
            dump.main()
        doc,array=replay.load_dump(self.root,'field')
        self.assertEqual(doc['execution_status'],'complete')
        self.assertEqual(array.shape,(1,2,2,3))
        out.write_bytes(b'corrupted array')
        with self.assertRaisesRegex(ValueError,'hash'):
            replay.load_dump(self.root,'field')

    def test_replay_refuses_mismatched_metadata_and_even_frames(self):
        meta=dict(frames=[1,3],crop=[0,0,2,2],width=2,height=2)
        replay.require_matching_dumps([meta,dict(meta),dict(meta)])
        for changed in (dict(meta,frames=[1,5]),dict(meta,crop=[2,0,2,2]),dict(meta,width=4),dict(meta,source_sha256='new')):
            with self.assertRaisesRegex(ValueError,'mismatch'):
                replay.require_matching_dumps([meta,changed,dict(meta)])
        even=dict(meta,frames=[0,2])
        with self.assertRaisesRegex(ValueError,'odd'):
            replay.require_matching_dumps([even,even,even])

    def test_replay_refuses_wrong_shape_nan_and_incomplete_dump(self):
        p=self.root/'field.json'
        meta=dict(frames=[1],crop=[0,0,2,2],width=2,height=2)
        p.write_text(json.dumps(meta))
        for values in (np.zeros((1,3,2,3),np.float32),np.full((1,2,2,3),np.nan,np.float32)):
            np.save(self.root/'field.npy',values)
            with self.assertRaisesRegex(ValueError,'finite float array'):
                replay.load_dump(self.root,'field')
        p.write_text(json.dumps(dict(meta,execution_status='incomplete')))
        with self.assertRaisesRegex(ValueError,'incomplete'):
            replay.load_dump(self.root,'field')

    def test_replay_failure_invalidates_old_report(self):
        report=self.root/'replay.json';report.write_text('{"execution_status":"complete"}')
        (self.root/'cal-static.json').write_text('{"execution_status":"incomplete"}')
        with patch('sys.argv',['replay.py',str(self.root),'--ffmpeg','never']):
            with self.assertRaisesRegex(ValueError,'incomplete'):
                replay.main()
        self.assertEqual(json.loads(report.read_text())['execution_status'],'incomplete')

    def test_replay_refuses_incomplete_or_changed_render(self):
        p=self.root/'previous.mkv';p.write_bytes(b'old video')
        record=p.with_suffix('.json')
        record.write_text('{"execution_status":"incomplete"}')
        with self.assertRaisesRegex(ValueError,'incomplete'):
            replay.load_render_record(p)
        record.write_text(json.dumps(dict(execution_status='complete',source_frames=2,output_frames=4,output_sha256='wrong')))
        with self.assertRaisesRegex(ValueError,'hash'):
            replay.load_render_record(p)


if __name__=='__main__':
    unittest.main()
