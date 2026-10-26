"""Affected host composition only; no SSH, worker or hardware launch."""
from pathlib import Path
import ast, copy, hashlib, importlib.util, inspect, json, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reattach_host_under_test',HERE/'host.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class AffectedHost(unittest.TestCase):
    def test_frozen_sources_and_request_tuple(self):
        pins,values=h.source_check()
        review={'adoption':{'version':'#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026','serial_sha256':'a'*64,'compatible_sha256':'b'*64,'rootfs':'c'*64,'transaction_id':'usb-irq-protection-activate-fixture-001'},
          'boot_id':'00000000-0000-4000-8000-000000000001','guard_path':'/var/lib/samurai/usb-irq-protection-activate-fixture-001-adopted/boot-id-private.txt',
          'guard_sha256':h.sha(b'00000000-0000-4000-8000-000000000001\n')}
        request=h.make_request('charger-reattach-update-fixture-001',review,pins['worker']['sha256'],values['payload'])
        worker=h.load(pins['worker']['path'],'test_actual_pure_update_schema')
        files,_=worker.unpack_request(request)
        self.assertEqual(len(files),2);self.assertEqual(request['old_manifest_sha256'],h.OLD)
        self.assertEqual(request['new_manifest_sha256'],h.NEW);self.assertEqual(len(request['lease_token']),48)
        for tx in ['charging-update-r8','charger-reattach-update-../bad','charger-reattach-update-short']:
            with self.assertRaises(ValueError):h.make_request(tx,review,pins['worker']['sha256'],values['payload'])

    def test_full_preflight_never_reaches_launch_claim(self):
        current={'private_directory':'fixture-read-only','result':{'eligible':False,'reason':'full_state_not_restorable'}}
        with patch.object(h,'preflight',return_value=current),patch.object(h,'transport_module',side_effect=AssertionError('must not launch')):
            result=h.launch('charger-reattach-update-fixture-001',True)
        self.assertFalse(result['launched']);self.assertEqual(result['charging_mutations'],0)

    def test_explicit_window_and_only_managed_reaches_original_transfer(self):
        calls=[];current={'private_directory':'fixture','result':{'eligible':True}}
        transport=SimpleNamespace(transfer=lambda *args:calls.append(args) or {'once':True})
        with patch.object(h,'preflight',return_value=current) as pre,patch.object(h,'transport_module',return_value=transport):
            with self.assertRaises(ValueError):h.launch('charger-reattach-update-fixture-001',False)
            pre.assert_not_called()
            self.assertEqual(h.launch('charger-reattach-update-fixture-001',True),{'once':True})
        self.assertEqual(calls,[('launch','charger-reattach-update-fixture-001',True)])

    def test_original_owned_transfer_only_adds_compression(self):
        import io
        pins,values=h.source_check()
        module=h.transport_module()
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);tx='charger-reattach-update-fixture-001'
            request={'transaction_id':tx,'identity':{'boot_id':'fixture-boot'}};raw=json.dumps(request).encode()
            (out/'stage-worker.py').write_bytes(values['worker'])
            binding={'endpoint':{'peer':module.PEER,'host_key_alias':module.ALIAS,'observed_new_boot':'fixture-boot'}}
            calls=[]
            class FakeOwnedChild:
                def __init__(self,argv,**kwargs):
                    self.pid=123;self.returncode=None;self.stdin=io.BytesIO();self.stream=kwargs['stdout'];self.waits=0;self.argv=argv;calls.append(self)
                def communicate(self,input):
                    self.sent=input
                    self.stream.write(json.dumps({'transaction_id':tx,'request_sha256':h.sha(raw),'launched':True}).encode());self.returncode=0
                def wait(self):self.waits+=1;return self.returncode
            with patch.object(module,'bound',return_value=(out,binding,request,raw,pins)),patch.object(module,'subprocess',SimpleNamespace(Popen=FakeOwnedChild)):
                reply=module.transfer('launch',tx,True)
                with self.assertRaises(ValueError):module.transfer('launch',tx,True)
            self.assertEqual(len(calls),1);child=calls[0]
            self.assertEqual(child.argv[1:4],['-C','-6','-T']);self.assertEqual(child.waits,1);self.assertTrue(child.stdin.closed)
            self.assertIn(values['remote'],child.sent)
            terminal=json.loads((out/'launch-transport-private/transport-terminal-private.json').read_bytes())
            self.assertTrue(terminal['terminal']);self.assertEqual(terminal['returncode'],0)
            self.assertEqual(reply['action'],'launch')

    def test_preflight_keeps_response_request_and_readonly_source_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);request={'schema':'fixture-only'};raw=json.dumps(request).encode()
            worker=b'# harmless fixture only\n'
            (out/'stage-worker.py').write_bytes(worker)
            captured=[]
            response={'schema':'samurai-charger-reattach-preflight-v1','request_sha256':h.sha(raw),'identity_match':True,'eligible':False}
            profile=SimpleNamespace(send_readonly=lambda p,code:captured.append((p,code)) or copy.deepcopy(response))
            bound=(out,{},request,raw,{'preflight_profile':{'path':'fixture-only'}})
            with patch.object(h,'bound',return_value=bound),patch.object(h,'load',return_value=profile):
                result=h.preflight('charger-reattach-update-fixture-001')
                self.assertFalse(result['result']['eligible']);self.assertEqual(len(captured),1)
                self.assertTrue(captured[0][1].endswith(worker));self.assertIn(b"'--preflight'",captured[0][1])
                self.assertNotIn(b'--execute-stage',captured[0][1]);self.assertFalse((out/'launch-intent-private.json').exists())
                response['request_sha256']='0'*64
                with self.assertRaises(ValueError):h.preflight('charger-reattach-update-fixture-001')

    def test_bound_rejects_changed_request_worker_and_does_not_reaudit_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            top=Path(folder);tx='charger-reattach-update-fixture-001';out=top/tx;out.mkdir()
            here=top/'source';here.mkdir();(here/'source-pins.json').write_bytes(b'fixture-pins')
            raw=json.dumps({'transaction_id':tx,'worker_sha256':h.sha(b'worker')}).encode()
            binding={'transaction_id':tx,'request_sha256':h.sha(raw),'source_pins_sha256':h.sha(b'fixture-pins'),'generated_from_actual_IRQ_adoption':True}
            (out/'request-private.json').write_bytes(raw);(out/'binding-private.json').write_text(json.dumps(binding));(out/'stage-worker.py').write_bytes(b'worker')
            pins={'worker':{'sha256':h.sha(b'worker')}}
            with patch.object(h,'HERE',here),patch.object(h,'PRIVATE',top),patch.object(h,'source_check',return_value=(pins,{})),patch.object(h,'load',side_effect=AssertionError('status/fetch must not launch/review current pointer')):
                self.assertEqual(h.bound(tx)[3],raw)
                (out/'request-private.json').write_bytes(raw+b' ')
                with self.assertRaises(ValueError):h.bound(tx)
                (out/'request-private.json').write_bytes(raw);(out/'stage-worker.py').write_bytes(b'changed')
                with self.assertRaises(ValueError):h.bound(tx)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AffectedHost))
    raise SystemExit(0 if result.wasSuccessful() else 1)
