"""Only new rollback/start wiring. All identities/processes/transports are synthetic."""
from pathlib import Path
import base64, contextlib, copy, hashlib, importlib.util, json, os, subprocess, sys, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.dont_write_bytecode=True
import sources, proof, controller
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rollback_operator',HERE/'fastboot-operator.py')
operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
sources.source_check()
worker=sources.load('rollback_worker');binder=sources.load('rollback_binder')
payload=sources.local(binder.source_check()['payload']['path']).read_bytes()
cases=[]

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(proof.encode(value) if not isinstance(value,bytes) else value)

def fixture(profile='booted_irq_new_resident'):
    source=dict(boot_id='11111111-1111-4111-8111-111111111111',version=proof.VERSION,
                serial_sha256='1'*64,compatible_sha256='2'*64,rootfs_sha256='3'*64)
    ident=dict(source)
    if profile!=worker.PROFILES[0]:ident['boot_id']='22222222-2222-4222-8222-222222222222'
    activation=None
    boot=proof.IRQ_BOOT if profile==worker.PROFILES[1] else proof.BOOT
    if profile!=worker.PROFILES[0]:
        activation={name:'4'*64 for name in ['context_sha256','guard_sha256','flash_request_sha256','flash_result_sha256','reboot_request_sha256','reboot_result_sha256']}
        activation.update(schema='samurai-irq-rollback-saved-activation-binding-v1',activation_transaction_id='usb-irq-protection-activate-synthetic-001',
            flash_claimed_ns=10,reboot_claimed_ns=20,boot_sha256=boot,retained_logdump_sha256=proof.LOGDUMP,
            action_pair=['flash-candidate','reboot-candidate'] if profile==worker.PROFILES[1] else ['rollback-original','reboot-original'])
    req=dict(schema='samurai-usb-irq-protection-rollback-request-v1',transaction_id='usb-irq-protection-rollback-synthetic-001',profile=profile,
        identity=ident,source_identity=source,source_stage={'transaction_id':'usb-irq-protection-stage-synthetic-001'},activation=activation,
        payload_sha256=worker.ROLLBACK_PAYLOAD,payload_base64=base64.b64encode(payload).decode(),worker_sha256=proof.WORKER,lease_token='a'*48)
    raw=proof.encode(req);h=proof.sha(raw);root='/root/charging-management-20261023/'+req['transaction_id']
    qargv=['python3','-B',root+'/restore-worker.py','--execute-rollback'];sargv=['python3','-B',root+'/rollback-supervisor.py','--execute-supervisor']
    common=dict(transaction_id=req['transaction_id'],boot_id=ident['boot_id'],request_sha256=h)
    w=dict(common,pid=101,start_ticks=201,argv=qargv,worker_sha256=proof.WORKER)
    launch=dict(common,pid=101,start_ticks=201,argv=qargv,supervisor_pid=102)
    end=dict(launch,terminal=True,returncode=0)
    sup=dict(common,pid=102,start_ticks=202,argv=sargv)
    se=dict(sup,terminal=True,returncode=0,worker_pid=101,worker_returncode=0)
    value=dict(schema='samurai-usb-irq-protection-rollback-result-v1',transaction_id=req['transaction_id'],profile=profile,terminal=True,
        restored=True,phase='staged_original',status='staged_original/runtime_pending',runtime_pending=True,disk_state='all_original_fsynced',
        stop_verified=True,primary_error=None,unknown_write_state=False,actual_resident_notes=worker.expected_profile(req)[1],
        final_files={name:dict(sha256=digest,mode='0o600',classification='original') for name,digest in worker.OLD_FILES.items()},
        temporary_files={name:dict(state='absent') for name in worker.OLD_FILES},automatic_replay_or_rollback=False,
        module_or_carrier_action=False,old_modules_resident_verified=False,original_full_runtime_accepted=False)
    objects={'result.json':value,'process-private.json':w,'launch-receipt-private.json':sup,
        'worker-launch-receipt-private.json':launch,'worker-terminal-private.json':end,
        'supervisor-process-private.json':sup,'supervisor-terminal-private.json':se,
        'before-private.json':{'read_end':8.0},'stopped-private.json':{'read_end':9.0},'after-private.json':{'read_end':10.0}}
    response=dict(transaction_id=req['transaction_id'],request_sha256=h,worker_terminal_verified=True,worker_terminal=end,worker_result=value,
        process=dict(state='absent',pid=101),supervisor_process=dict(state='zombie',pid=102,start_ticks=202),
        files={name:dict(bytes=len(proof.encode(v)),sha256=proof.sha(proof.encode(v)),base64=base64.b64encode(proof.encode(v)).decode()) for name,v in objects.items()},
        identity_observation=dict(source_boot_same=True,identity_matches=True,boot_id=ident['boot_id']),
        identity_after=dict(source_boot_same=True,identity_matches=True,boot_id=ident['boot_id']))
    paths=proof.remote_paths(req['transaction_id'])
    names={'result':'result.json','worker_process':'process-private.json','supervisor_launch':'launch-receipt-private.json',
        'worker_launch':'worker-launch-receipt-private.json','worker_terminal':'worker-terminal-private.json',
        'supervisor_process':'supervisor-process-private.json','supervisor_terminal':'supervisor-terminal-private.json',
        'before':'before-private.json','stopped':'stopped-private.json','after':'after-private.json'}
    evidence={key:dict(path=paths[key],sha256=proof.sha(proof.encode(objects[name]))) for key,name in names.items()}
    for key,data in {'request':raw,'worker_source':sources.local(sources.pins()['baseline']['rollback_worker']['path']).read_bytes(),
                     'supervisor_source':sources.local(sources.pins()['baseline']['rollback_supervisor']['path']).read_bytes()}.items():
        evidence[key]=dict(path=paths[key],sha256=proof.sha(data))
    current=dict(identity=ident,release=proof.RELEASE,machine='aarch64',taint='0',notes=worker.expected_profile(req)[1],
        module_states={name:'live' for name in worker.OLD_NOTES},boot=dict(bytes=100663296,sha256=boot),logdump=dict(bytes=67108864,sha256=proof.LOGDUMP))
    review=dict(request=req,result_sha256=proof.sha(proof.encode(value)),host_binding_sha256='b'*64,result=value,identity=ident,current=current,
        rollback=dict(transaction_id=req['transaction_id'],request_sha256=h,result_sha256=proof.sha(proof.encode(value)),host_binding_sha256='b'*64,
                      worker_sha256=proof.WORKER,supervisor_sha256=proof.SUPERVISOR,evidence=evidence),
        post_restore_probe=dict(stdin_sha256='c'*64,stdout_sha256='d'*64,child_sha256='e'*64,terminal_sha256='f'*64))
    return req,response,review

def imported(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Delta(unittest.TestCase):
    def test_01_rollback_terminal_and_profiles(self):
        for profile in worker.PROFILES:
            req,response,review=fixture(profile);proof.validate_records(req,proof.encode(req),response,worker)
            guard=proof.make_guard('usb-irq-protection-rollback-activate-synthetic-001','a'*48,review)
            self.assertEqual(guard['resident_notes'],worker.expected_profile(req)[1]);self.assertFalse(guard['runtime_validation_accepted'])
        req,response,_=fixture()
        for label,change in [('worker-failed',lambda r:r['worker_terminal'].update(returncode=1)),
                             ('worker-alive',lambda r:r['process'].update(state='alive')),
                             ('supervisor-reused',lambda r:r['supervisor_process'].update(start_ticks=999)),
                             ('unknown-write',lambda r:r['worker_result'].update(unknown_write_state=True))]:
            bad=copy.deepcopy(response);change(bad)
            with self.assertRaises(ValueError):proof.validate_records(req,proof.encode(req),bad,worker)
        cases.append('three actual profile mappings; failed/alive/reused/changed original rollback rejected')

    def test_02_post_restore_probe_and_path_mapping(self):
        req,response,review=fixture();expected=proof.post_probe_request(req,review['result_sha256'],review['host_binding_sha256'])
        report=dict(schema=expected['schema'],request=expected,current=review['current'],identity_before=req['identity'],identity_after=req['identity'],
                    started_boottime_ns=11_000_000_000,ended_boottime_ns=12_000_000_000)
        proof.validate_probe(report,expected,req,{'read_end':10.0},worker)
        for label,change in [('old-envelope',lambda r:r['request'].update(purpose='pre-restore')),
            ('cross-boot',lambda r:r['identity_after'].update(boot_id='33333333-3333-4333-8333-333333333333')),
            ('before-restore',lambda r:r.update(started_boottime_ns=9_000_000_000)),('wrong-notes',lambda r:r['current']['notes'].update({'samurai-usb-input':'0'*64}))]:
            bad=copy.deepcopy(report);change(bad)
            with self.assertRaises((ValueError,RuntimeError)):proof.validate_probe(bad,expected,req,{'read_end':10.0},worker)
        with tempfile.TemporaryDirectory(prefix='synthetic-rollback-review-') as temp:
            temp=Path(temp);directory=temp/'rollback'/req['transaction_id'];fetch=directory/'fetch-synthetic-private';probe=temp/'probe'
            fetch.mkdir(parents=True);probe.mkdir();write(directory/'binding-private.json',{'synthetic':True});write(directory/'restore-worker.py',sources.local(sources.pins()['baseline']['rollback_worker']['path']).read_bytes());write(fetch/'job-private.json',{'action':'fetch'})
            write(probe/'child-private.json',{'synthetic':True});write(probe/'terminal-private.json',{'synthetic':True})
            binding_sha=proof.sha((directory/'binding-private.json').read_bytes());expected=proof.post_probe_request(req,review['result_sha256'],binding_sha)
            report=dict(schema=expected['schema'],request=expected,current=review['current'],identity_before=req['identity'],identity_after=req['identity'],started_boottime_ns=11_000_000_000,ended_boottime_ns=12_000_000_000)
            fake_host=SimpleNamespace(PRIVATE=directory.parent,source_check=lambda:None,
                bound=lambda *a,**k:(directory,{'endpoint':{'peer':proof.PEER}},req,proof.encode(req),{}),terminal_job=lambda p:({'returncode':0},response),review_launch_transport=lambda *a:None)
            seen=[]
            fake_auth=SimpleNamespace(source_check=lambda:None,saved_transport=lambda p,*a:(seen.append(p) or proof.encode(report),b'',{'returncode':0,'primary_error':None,'cleanup_errors':[]}))
            real_local=sources.local;real_load=sources.load
            def mapped(value):return probe.resolve() if str(value)=='E:/synthetic/probe' else real_local(value)
            def load(name):return {'rollback_host':fake_host,'rollback_worker':worker,'auth_host':fake_auth}.get(name) or real_load(name)
            with patch.object(sources,'local',side_effect=mapped),patch.object(sources,'load',side_effect=load):
                got=proof.review_completed(directory,fetch,'E:/synthetic/probe')
            self.assertEqual(seen,[probe.resolve()]);self.assertEqual(got['post_restore_probe_directory'],str(probe.resolve()))
            fake_auth.saved_transport=lambda *a:(proof.encode(report),b'',{'returncode':1})
            with patch.object(sources,'load',side_effect=load),self.assertRaises(ValueError):proof.review_completed(directory,fetch,probe)
        cases.append('post-restore actual validator rejects stale/old/cross-boot/wrong notes; review normalizes E:/ probe before auth/read and rejects transport failure')

    def test_03_bind_remote_full_request_and_once_owner(self):
        req,response,review=fixture();base=controller.owner()
        with tempfile.TemporaryDirectory(prefix='synthetic-rollback-bind-') as temp:
            temp=Path(temp);root=temp/'host';tx='usb-irq-protection-rollback-activate-synthetic-001'
            with patch.object(proof,'review_completed',side_effect=ValueError('no actual rollback')):
                with self.assertRaises(ValueError):controller.bind(tx,'missing','missing','missing',private=root)
            self.assertFalse(root.exists())
            with patch.object(proof,'review_completed',return_value=review):controller.bind(tx,'rollback','fetch','probe',private=root)
            directory,request,binding,_=controller.bound(tx,private=root)
            self.assertIn('proof.py',request['files'])
            with patch.object(proof,'review_completed',return_value=review),self.assertRaises(ValueError):controller.bind(tx,'rollback','fetch','probe',private=root)
            # Run the new complete request through the real remote prepare
            # install/allowlist. Only proc and the hardware preflight are fake.
            remote=imported(HERE/'remote.py','synthetic_remote');fakefs=temp/'device-fs';fakefs.mkdir()
            def p(value,*parts):
                text=str(value)
                return Path(fakefs/text.lstrip('/'),*parts) if text.startswith(('/proc','/run','/var/lib')) else Path(value,*parts)
            write(p('/proc/mounts'),b'tmpfs /run tmpfs rw 0 0\n');write(p('/proc/sys/kernel/random/boot_id'),(request['expected_boot']+'\n').encode())
            p('/run').mkdir(exist_ok=True)
            remote.OWNER=p('/run/new-owner.json')
            def preflight(data,path,**kwargs):
                common=(path/'common.py').read_text()
                constants={}
                import ast
                for node in ast.parse(common).body:
                    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='PROOF_SHA':constants['sha']=ast.literal_eval(node.value)
                self.assertEqual(constants['sha'],proof.sha((path/'proof.py').read_bytes()))
            with patch.object(remote,'Path',side_effect=p),patch.object(remote,'preflight',side_effect=preflight):
                bad=copy.deepcopy(request);bad['files'].pop('proof.py')
                with self.assertRaises(ValueError):remote.prepare(bad,temp/'missing-proof-device')
                self.assertFalse(remote.OWNER.exists())
                value=remote.prepare(request,temp/'device-transaction')
                self.assertTrue(value['prepared']);self.assertEqual((temp/'device-transaction/proof.py').read_bytes(),(HERE/'proof.py').read_bytes())
            calls=[]
            def start(directory,action,request,pins,endpoint):calls.append((action,request));return {'pending':True,'no_replay':True}
            with patch.object(proof,'review_completed',return_value=review):
                got=base.run('prepare',tx,True,True,private=root,start=start);self.assertTrue(got['pending'])
                with self.assertRaises(ValueError):base.run('prepare',tx,True,True,private=root,start=start)
            self.assertEqual(len(calls),1);self.assertEqual(calls[0][1],request)
        cases.append('missing originals zero bind; full six-file request actually passes remote allowlist/install; run -> real new bound/source-pins -> one pending prepare, no redispatch')

    def test_04_device_proof_hash_rejected_before_source_load(self):
        common=imported(HERE/'common.py','synthetic_device_common')
        called=[]
        with patch.object(common,'secure_file',side_effect=lambda p:p),patch.object(common,'file_sha',return_value='0'*64),patch.object(common.runpy,'run_path',side_effect=lambda p:called.append(p)):
            with self.assertRaises(ValueError):common.rollback_material({'transaction_id':'usb-irq-protection-rollback-activate-synthetic-001'})
        self.assertEqual(called,[])
        cases.append('actual device rollback_material rejects wrong proof source SHA before loading code or accessing rollback records')

    def test_05_export_consumed_by_operator_and_actual_worker(self):
        req,response,review=fixture();base=controller.owner();fb=operator.owner()
        with tempfile.TemporaryDirectory(prefix='synthetic-rollback-context-') as temp:
            temp=Path(temp);tx='usb-irq-protection-rollback-activate-synthetic-001';directory=temp/tx;directory.mkdir()
            token='a'*48;guard=proof.make_guard(tx,token,review);write(directory/'guard-private.json',guard)
            write(directory/'binding-private.json',dict(rollback_directory='rollback',rollback_fetch_directory='fetch',post_restore_probe_directory='probe'))
            ident=dict(transaction_id=tx,token=token,boot_id=guard['boot_id']);root='/root/charging-management-20261023/'+tx
            write(directory/'quiesce-state-private.json',dict(ident,pid=301,terminal=True,exit_code=0));write(directory/'quiesce-summary-private.json',dict(ident,taint=0))
            write(directory/'quiesce-boot-id-private.txt',(guard['boot_id']+'\n').encode())
            write(directory/'quiesce-process-private.json',dict(ident,pid=301,startticks=401,argv=['python3','-B',root+'/eud-quiesce.py','--guard',root+'/guard-private.json','--commit-quiesce'],status='absent'))
            claim=dict(ident,schema='samurai-eud-restart-host-claim-v1',guard_sha256=proof.sha((directory/'guard-private.json').read_bytes()),request_count=1,
                worker_sha256=sources.worker_hashes()['eud-restart.py'],argv=['python3','-B',root+'/eud-restart.py','--guard',root+'/guard-private.json','--commit-restart2-bootloader'])
            write(directory/'restart-claim-private.json',claim);write(directory/'restart-job-private.json',{'job':'synthetic-original-job'})
            terminal=dict(pid=302,startticks=402,argv=['synthetic-original-ssh'],terminal=True,returncode=255)
            with patch.object(base,'terminal_job',return_value=(terminal,b'')):context=controller.export_context(directory)
            path=directory/'host-context-private.json'
            with patch.object(proof,'review_completed',return_value=review):
                self.assertEqual(operator.validate_context(path),context)
                # Original operator deliberately cannot validate this different
                # context; the adapter is required, not an invented old shape.
                original=sources.load('fastboot_operator')
                with self.assertRaises(ValueError):original.validate_context(path)
                work=directory/'fastboot-operator/rollback-original';work.mkdir(parents=True)
                image=SimpleNamespace(stat=lambda:SimpleNamespace(st_size=100663296))
                inputs={'synthetic':'only pinned artifacts boundary'};identity=temp/'identity.json';write(identity,{'serial':'synthetic-serial'})
                realsha=fb.sha
                calls=[]
                def command(where,label,argv):
                    calls.append(argv);write(where/(label+'-command-private.json'),{'synthetic':True});write(where/(label+'-terminal-private.json'),{'terminal':True,'returncode':0})
                    if label=='devices':return ('synthetic-serial fastboot\n','')
                    if label=='product':return ('','product: msmnile\n')
                    if label.endswith('-size'):
                        part=label[:-5];return ('','partition-size:'+part+': '+str(fb.SIZES[part])+'\n')
                    if label=='flash-boot':return ('',"Writing 'boot' OKAY\n")
                    raise AssertionError('unexpected command '+label)
                request=dict(schema='samurai-usb-irq-protection-fastboot-action-v1',execute_authorized=True,window_confirmed=True,action='rollback-original',
                    transaction_id=tx,token=token,old_boot_id=guard['boot_id'],context_path=str(path),context_sha256=realsha(path),
                    operator_sha256=realsha(HERE/'fastboot-operator.py'),inputs=inputs,claimed_ns=123)
                write(work/'request-private.json',request)
                with patch.object(fb,'locked',side_effect=lambda p:contextlib.nullcontext()),patch.object(fb,'process_info',return_value={'synthetic':True}),\
                     patch.object(fb,'local_inputs',return_value=inputs),patch.object(fb,'IDENTITY',identity),patch.object(fb,'command',side_effect=command),\
                     patch.object(fb,'IMAGES',{'original':{'boot':(image,proof.BOOT,100663296)}}),patch.object(fb,'sha',side_effect=lambda p:proof.BOOT if p is image else realsha(p)),\
                     patch.object(fb,'windows_path',return_value='synthetic-original-boot.img'):
                    fb.worker(work/'request-private.json')
                    value=json.loads((work/'result-private.json').read_bytes());self.assertTrue(value['passed']);self.assertEqual(value['partitions_written'],['boot'])
                    with self.assertRaises((ValueError,FileExistsError)):fb.worker(work/'request-private.json')
                    with self.assertRaises(ValueError):fb.run_action('flash-candidate','synthetic-serial',lambda *a:(_ for _ in ()).throw(AssertionError('must not call USB')))
                self.assertEqual([c[3] for c in calls if 'flash' in c],['flash'])
                self.assertFalse(any('reboot' in c for c in calls));self.assertFalse(value['rootfs_rollback_proven'])
            with patch.object(proof,'review_completed',side_effect=ValueError('missing actual rollback')),self.assertRaises(ValueError):operator.validate_context(path)
        cases.append('actual export seven raws accepted by new operator (SSH255 remains unproved), old operator rejects; original owner.worker consumes exact new request/context, only explicit boot rollback, duplicate worker and forward flash rejected')

    def test_06_worker_cli_dispatch(self):
        seen=[]
        with patch.object(operator,'owner',return_value=SimpleNamespace(worker=lambda p:seen.append(p))),patch.object(sys,'argv',['adapter','--_worker','synthetic-request.json']):
            self.assertEqual(operator.main(),0)
        self.assertEqual(seen,['synthetic-request.json'])
        cases.append('real operator --_worker CLI enters the existing worker exactly once')

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Delta)
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    result=dict(passed=outcome.wasSuccessful(),methods=outcome.testsRun,cases=cases,
                actual_device_or_USB_or_SDK=False,synthetic_temporary_material_only=True,
                boundary_fakes=['transport authentication/OS identities and hardware preflight','source artifact reads and fastboot commands in owner.worker test'],
                tested_files={name:proof.sha((HERE/name).read_bytes()) for name in ['proof.py','controller.py','common.py','remote.py','fastboot-operator.py','test-delta.py']})
    (HERE/'test-result.json').write_bytes(proof.encode(result))
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
