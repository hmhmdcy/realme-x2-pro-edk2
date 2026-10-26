"""Targeted host composition checks. Models are never phone evidence."""
from pathlib import Path
from unittest.mock import patch
import ast, copy, hashlib, importlib.util, json, os, re, sys, tempfile, unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import host,adopt
fixture=host.load(host.DEVICE/'test-device.py','pm_host_explicit_fixture')

class HostChecks(unittest.TestCase):
    def test_window_reuses_only_same_verified_source_bytes(self):
        window=host.load(HERE/'activation-window.py','pm_window_source_test')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source';path.write_bytes(b'actual retained source')
            calls=[]
            def review(stage,fetched):calls.append(1);return path.read_bytes(),{'stage':stage,'fetch':fetched}
            retained,reads=window.cached_review(review,'stage','fetch')
            self.assertEqual(len(reads),1);self.assertEqual(retained('stage','fetch')[0],b'actual retained source')
            self.assertEqual(len(calls),1)
            with self.assertRaisesRegex(ValueError,'different source'):retained('other','fetch')
            path.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError,'source changed'):retained('stage','fetch')

    def test_path_operator_restore_profile_wiring(self):
        from types import SimpleNamespace
        profile=host.load(HERE/'rollback-profile.py','pm_restore_path_test')
        binder=profile.binder();saved=SimpleNamespace(OPERATOR_PATH=None)
        def reviewed(*args):return saved.OPERATOR_PATH,args
        saved.review_profile_sources=reviewed
        with patch.object(binder,'source_check',return_value={}),patch.object(profile,'load',return_value=saved):
            operator,args=binder.review_sources('booted_504_new_resident','stage','fetch','context')
        self.assertEqual(operator,HERE/'fastboot-operator.py')
        self.assertEqual(args,('booted_504_new_resident','stage','fetch','context'))
        original=SimpleNamespace(load=lambda name:('original',name))
        profile.recovery_sources(original)
        self.assertEqual(original.load('other'),('original','other'))
        self.assertTrue(callable(original.load('rollback_binder').review_current))
        self.assertTrue(callable(original.load('rollback_host').transfer))

    def test_both_actual_audits_and_profile_request_binding(self):
        for profile in ('forward_504','restored_502'):
            raw,request=fixture.fixture(profile)
            actual=dict(profile=profile,guard=request['activation_guard'],context_sha256=request['context_sha256'],
                        guard_sha256=request['guard_sha256'],activation_transaction_id=request['activation_transaction_id'])
            g=request['guard'];actual['guard'].update(kernel_release=g['kernel_release'],rootfs_release_sha256=g['rootfs_release_sha256'],
                        soc_serial_sha256=g['soc_serial_sha256'],compatible_sha256=g['compatible_sha256'])
            stage=dict(transaction_id=request['stage']['transaction_id'],stage_result=request['stage'],result_sha256=request['stage_result_sha256'])
            proof=dict(actual=actual,stage=stage,new_boot_id=request['new_boot_id'],stdout_sha256='a'*64,payload_sha256='b'*64,terminal_sha256='c'*64)
            with tempfile.TemporaryDirectory() as temp:
                camera=Path(temp)/'camera.json'
                # The exact formal camera bytes come from a retained actual request.
                cached=json.loads(fixture.old_request)['camera']; camera.write_bytes((json.dumps(cached)+'\n').encode())
                with patch.object(host,'review_probe',return_value=proof),patch.object(host,'CAMERA',host.sha(camera.read_bytes())):
                    made=host.make_request('unused',camera,'unused')
                self.assertEqual(made['guard'],g)
                self.assertEqual(made['profile'],profile)
                audited=host.device_module().audit(raw,made)
                self.assertTrue(audited['passed'],audited);self.assertEqual(len(audited['checks']),12)
                bad=copy.deepcopy(made);bad['profile']='restored_502' if profile=='forward_504' else 'forward_504'
                with self.assertRaises(AssertionError):host.device_module().validate_request(bad)
                code=adopt.payload(dict(profile=profile))
                ast.parse(code)
                self.assertIn(b"len(verified['checks'])==12",code)
                self.assertIn(b"adoption['version']==PROFILES[adoption['profile']]['version']",code)

    def test_original_actual_saved_transport_and_tamper(self):
        directory=fixture.CACHED;code=(directory/'executed-device-source.py').read_bytes()
        stdout,_,terminal=host.saved_transport(directory,code,host.PEER,collection=True)
        self.assertEqual(terminal['returncode'],0);self.assertTrue(json.loads(stdout)['result']['passed'])
        with self.assertRaises(ValueError):host.saved_transport(directory,code+b'\n',host.PEER,collection=True)
        self.assertIn('-C',host.transport_argv(host.PEER))
        self.assertIn('StrictHostKeyChecking=yes',host.transport_argv(host.PEER))

    def test_unsupported_context_and_recovery_module_cleanup(self):
        before={key:sys.modules.get(key) for key in ('sources','proof')}
        with host.recovery_modules() as (operator,proof):
            self.assertEqual(operator.owner().ACTIONS,('inspect','rollback-original','reboot-original'))
            self.assertTrue(callable(proof.review_completed))
        self.assertEqual(before,{key:sys.modules.get(key) for key in before})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'host-context-private.json';path.write_text('{"schema":"old-or-unknown"}')
            with self.assertRaisesRegex(ValueError,'unsupported actual activation context'):host.completed(path)

    def test_fresh_adoption_guard_and_failure_before_creation(self):
        for profile in ('forward_504','restored_502'):
            raw,request=fixture.fixture(profile)
            result=host.device_module().audit(raw,request);self.assertTrue(result['passed'])
            tx=request['activation_transaction_id']
            with tempfile.TemporaryDirectory() as temp:
                target=Path(temp)/(tx+'-adopted')/'boot-id-private.txt'
                value=dict(schema='samurai-irq-native-usb-pm-adoption-v1',transaction_id=tx,profile=profile,guard=str(target),
                    postboot_request=request,boot=request['new_boot_id'],version=request['guard']['target_kernel_version'],
                    postboot_raw_sha256='a'*64,postboot_request_sha256='b'*64,stage_transaction_id=request['guard']['transaction_id'])
                code=adopt.payload(value).split(b"GUARD_ROOT=Path('/var/lib/samurai')",1)[1]
                tree=ast.parse(code);tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
                def collect(q,d):d.update(copy.deepcopy(raw))
                env=dict(Path=Path,re=re,os=os,json=json,hashlib=hashlib,GUARD_ROOT=Path(temp),collect=collect,
                         audit=lambda r,q:host.device_module().audit(r,q),PROFILES=host.device_module().PROFILES)
                exec(compile(tree,'<actual-adoption-tail-model>','exec'),env)
                with patch.dict(env,audit=lambda r,q:dict(passed=False,checks={},errors={'health':True},hardware_writes=0)):
                    with self.assertRaises(AssertionError):env['adopt_current_irq_boot'](value)
                self.assertFalse(target.parent.exists())
                reply=env['adopt_current_irq_boot'](value)
                self.assertTrue(reply['fresh_validation_passed']);self.assertEqual(target.read_text(),value['boot']+'\n')
                with self.assertRaises(AssertionError):env['adopt_current_irq_boot'](value)

if __name__=='__main__':unittest.main()
