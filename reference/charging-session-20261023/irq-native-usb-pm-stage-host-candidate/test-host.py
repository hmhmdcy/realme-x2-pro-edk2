"""Affected current-cohort host compositions. No real transport or device calls."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,copy,hashlib,importlib.util,inspect,io,json,tempfile,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_pm_stage_host_test',HERE/'host.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
TX='irq-native-usb-pm-stage-fixture-0001'
PINS=h.local('E:/edk2-samurai-out/charging-session-20261023/icon-capture-irq-reattach-runtime/identity-pins-private.json')

class AffectedHost(unittest.TestCase):
    def test_actual_completed_update_and_original_adoption_make_current_stage(self):
        pins,values=h.source_check();checked,base=h.review_runtime(PINS)
        self.assertEqual(checked['manifest_sha256'],h.OLD)
        self.assertEqual(base['pointer']['charging_manifest_sha256'],checked['base_adoption_manifest_sha256'])
        self.assertNotEqual(base['pointer']['charging_manifest_sha256'],h.OLD)
        self.assertFalse(checked['boot_adoption_pointer_rewritten'])
        request=h.make_request(TX,base,pins['worker']['sha256'],values['payload'])
        worker=h.load(pins['worker']['path'],'test_current_cold_stage_contract')
        files,manifest=worker.unpack(request)
        self.assertEqual(set(request),set(json.loads(values['worker_contract'])['request_keys']))
        self.assertEqual(set(files),set(worker.ORDER));self.assertEqual(h.sha(files[worker.MANIFEST]),h.NEW)
        self.assertEqual(request['identity']['boot_id'],checked['boot_id'])
        self.assertEqual(request['adoption']['guard_sha256'],checked['guard_sha256'])
        self.assertEqual(manifest['modules']['samurai-mp2650']['sha256'],'97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd')
        for tx in ['charger-reattach-update-fixture-0001','irq-native-usb-pm-stage-../bad','irq-native-usb-pm-stage-short']:
            with self.assertRaises(ValueError):h.make_request(tx,base,pins['worker']['sha256'],values['payload'])

    def test_forged_overlay_is_rejected_before_any_binding_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            top=Path(folder);private=top/'must-not-exist';path=top/'overlay.json'
            path.write_text(json.dumps({'schema':'samurai-icon-irq-runtime-update-v1',
                'review_inputs':{'base_adoption':{},'update_directory':'fixture'},'reviewed':{'manifest_sha256':'forged'}}))
            base={'boot_id':'fixture','guard_path':'fixture','guard_sha256':'fixture'}
            module=SimpleNamespace(base_module=lambda:SimpleNamespace(review_adoption=lambda **kw:base),
                review_update=lambda *args:{'manifest_sha256':h.OLD})
            with patch.object(h,'PRIVATE',private),patch.object(h,'load',return_value=module):
                with self.assertRaises(ValueError):h.bind(TX,path)
            self.assertFalse(private.exists())
            self.assertEqual(sorted(p.name for p in top.iterdir()),['overlay.json'])

    def test_window_and_healthy_full_only_reach_original_launch_after_preflight(self):
        calls=[];transport=SimpleNamespace(transfer=lambda *args:calls.append(args) or {'delegated':True})
        current={'private_directory':'fixture','result':{'eligible':True,'passed':True,'healthy_state':'full_holding'}}
        with patch.object(h,'preflight',return_value=current) as pre,patch.object(h,'transport_module',return_value=transport):
            with self.assertRaises(ValueError):h.launch(TX,False)
            pre.assert_not_called();self.assertEqual(h.launch(TX,True),{'delegated':True})
            current['result'].update(eligible=False,passed=False,reason='protection fault')
            result=h.launch(TX,True)
            self.assertFalse(result['launched']);self.assertEqual(result['charging_mutations'],0)
        self.assertEqual(calls,[('launch',TX,True)])

    def test_original_transfer_claim_eof_wait_and_two_substitution_remote(self):
        pins,values=h.source_check();module=h.transport_module()
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);request={'transaction_id':TX,'identity':{'boot_id':'fixture-boot'}};raw=json.dumps(request).encode()
            (out/'stage-worker.py').write_bytes(values['worker'])
            binding={'endpoint':{'peer':module.PEER,'host_key_alias':module.ALIAS,'observed_new_boot':'fixture-boot'}}
            calls=[]
            class Child:
                def __init__(self,argv,**kwargs):
                    self.pid=123;self.returncode=None;self.stdin=io.BytesIO();self.stream=kwargs['stdout'];self.waits=0;self.argv=argv;calls.append(self)
                def communicate(self,input):
                    self.sent=input;self.stream.write(json.dumps({'transaction_id':TX,'request_sha256':h.sha(raw),'launched':True}).encode());self.returncode=0
                def wait(self):self.waits+=1;return self.returncode
            with patch.object(module,'bound',return_value=(out,binding,request,raw,pins)),patch.object(module,'subprocess',SimpleNamespace(Popen=Child,PIPE=-1)):
                reply=module.transfer('launch',TX,True)
                with self.assertRaises(ValueError):module.transfer('launch',TX,True)
            self.assertEqual(len(calls),1);child=calls[0]
            self.assertEqual(child.argv[1:4],['-C','-6','-T']);self.assertEqual(child.waits,1);self.assertTrue(child.stdin.closed)
            self.assertTrue(child.sent.endswith(values['remote']))
            self.assertIn(b"out = root / 'device-stage'",values['remote'])
            term=json.loads((out/'launch-transport-private/transport-terminal-private.json').read_bytes())
            self.assertTrue(term['terminal']);self.assertEqual(term['returncode'],0);self.assertEqual(reply['action'],'launch')

    def test_readonly_preflight_keeps_source_request_response_and_no_launch_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);request={'schema':'fixture-only'};raw=json.dumps(request).encode();worker=b'# harmless fixture\n'
            (out/'stage-worker.py').write_bytes(worker);captured=[]
            response={'schema':'samurai-irq-native-usb-pm-preflight-v1','request_sha256':h.sha(raw),'identity_match':True,'eligible':True,'healthy_state':'full_holding'}
            profile=SimpleNamespace(send_readonly=lambda p,code:captured.append((p,code)) or copy.deepcopy(response))
            bound=(out,{},request,raw,{'preflight_profile':{'path':'fixture-only'}})
            with patch.object(h,'bound',return_value=bound),patch.object(h,'load',return_value=profile):
                result=h.preflight(TX);self.assertTrue(result['result']['eligible']);self.assertEqual(len(captured),1)
                self.assertTrue(captured[0][1].endswith(worker));self.assertIn(b"'--preflight'",captured[0][1])
                self.assertNotIn(b'--execute-stage',captured[0][1]);self.assertFalse((out/'launch-intent-private.json').exists())
                response['request_sha256']='0'*64
                with self.assertRaises(ValueError):h.preflight(TX)

    def test_retained_fetch_does_not_rebind_and_changed_originals_block_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            top=Path(folder);out=top/TX;out.mkdir();here=top/'source';here.mkdir();(here/'source-pins.json').write_bytes(b'fixture-pins')
            worker=b'worker';raw=json.dumps({'transaction_id':TX,'worker_sha256':h.sha(worker)}).encode()
            evidence=top/'immutable';evidence.write_bytes(b'actual-old-evidence')
            binding={'schema':'samurai-irq-native-usb-pm-stage-binding-v1','transaction_id':TX,'request_sha256':h.sha(raw),
                'source_pins_sha256':h.sha(b'fixture-pins'),'generated_from_actual_runtime_update':True,
                'reviewed':{'files':{'actual':{'path':str(evidence),'sha256':h.sha(b'actual-old-evidence')}}},
                'runtime_pins':{'path':str(evidence),'sha256':h.sha(b'actual-old-evidence')}}
            (out/'request-private.json').write_bytes(raw);(out/'binding-private.json').write_text(json.dumps(binding));(out/'stage-worker.py').write_bytes(worker)
            pins={'worker':{'sha256':h.sha(worker)}}
            with patch.object(h,'HERE',here),patch.object(h,'PRIVATE',top),patch.object(h,'source_check',return_value=(pins,{})),patch.object(h,'review_runtime',side_effect=AssertionError('fetch must not rebind')):
                evidence.write_bytes(b'later-pointer-or-boot')
                self.assertEqual(h.bound(TX)[3],raw)
                with self.assertRaises(ValueError):h.bound(TX,launching=True)
                (out/'request-private.json').write_bytes(raw+b' ')
                with self.assertRaises(ValueError):h.bound(TX)
                (out/'request-private.json').write_bytes(raw);(out/'stage-worker.py').write_bytes(b'changed')
                with self.assertRaises(ValueError):h.bound(TX)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AffectedHost))
    report={'passed':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'tested_files':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['host.py','test-host.py','remote.py','supervisor.py','source-pins.json']},
        'actual_cached_adoption_and_completed_update_reviewed':True,'device_accessed':False,'actual_runtime_request_published':False,'old_matrices_rerun':False}
    (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
