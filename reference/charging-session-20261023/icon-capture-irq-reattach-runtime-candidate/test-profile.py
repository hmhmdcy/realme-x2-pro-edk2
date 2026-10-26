"""Only the new saved-update/profile paths; synthetic identities never leave tmp."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast, base64, copy, hashlib, importlib.util, json, tarfile, tempfile, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode())


def main():
    review = load(HERE / 'update-review.py', 'test_actual_update_review')
    launcher = load(HERE / 'launcher.py', 'test_actual_runtime_launcher')
    binder = load(HERE / 'bind-identity.py', 'test_actual_runtime_bind')
    pins, values = review.check_sources()
    worker_path = REF / pins['update_worker']['path']
    host_path = REF / pins['update_host']['path']
    worker = load(worker_path, 'test_saved_worker_functions')
    host = load(host_path, 'test_original_update_host_bound')
    package = json.loads((HERE.parent / 'charger-reattach-observation-payload-candidate/payload-result.json').read_bytes())
    forward = review.local(package['forward']['path']).read_bytes()
    with tarfile.open(review.local(package['rollback']['path'])) as archive:
        old_manifest = archive.extractfile(worker.MANIFEST.lstrip('/')).read()
        old_ko = archive.extractfile(worker.KO.lstrip('/')).read()
    original_load = review.load
    cases = []
    def passed(name): cases.append(name)
    def rejects(name, action):
        try: action()
        except (ValueError, RuntimeError, OSError, KeyError, TypeError): passed(name)
        else: raise AssertionError('expected rejection: ' + name)
    cached = b'attempted=1 terminal=1 error=0\nsynthetic saved cache, not device evidence\n'
    # Actual health/unchanged/request functions run. Only the external cache
    # bytes/source-loader/clock/device files are modelled, never real receipts.
    cache_sha = review.sha(cached)

    with tempfile.TemporaryDirectory(prefix='icon-runtime-synthetic-') as tmp:
        root = Path(tmp); tx = 'charger-reattach-update-offline-fixture'
        out = root / tx; out.mkdir(); call = out / 'fetch-0123456789abcdef-private'; call.mkdir()
        actual_host_pins, _ = host.source_check()
        host.HERE = root / 'host-sources'; host.HERE.mkdir(); host.PRIVATE = root
        save(host.HERE / 'source-pins.json', {'synthetic': True})
        host.source_check = lambda: (actual_host_pins, {})
        boot = '11111111-2222-4333-8444-555555555555'
        adoption_tx = 'usb-irq-protection-activate-fixture0001'
        guard = '/var/lib/samurai/' + adoption_tx + '-adopted/boot-id-private.txt'
        ident = dict(boot_id=boot, version=worker.VERSION, serial_sha256='1'*64,
                     compatible_sha256='2'*64, rootfs_sha256='3'*64)
        key_path = review.local(actual_host_pins['key_transport']['path'])
        base = {'boot_id': boot, 'guard_path': guard, 'guard_sha256': review.sha((boot+'\n').encode()),
          'adoption': dict(transaction_id=adoption_tx, version=worker.VERSION, release=worker.RELEASE,
                           serial_sha256='1'*64, compatible_sha256='2'*64, rootfs='3'*64),
          'pointer': {'charging_manifest_sha256': review.OLD},
          'runtime_expected': {'release': worker.RELEASE, 'version': worker.VERSION, 'rootfs': '3'*64,
             'notes': {**{k.replace('-', '_'):v for k,v in worker.NOTES.items()}, 'qcom_camss': '6'*64, 's5k3m5': '7'*64}},
          'endpoint': {'kind':'usb-ipv6','peer':'fe80::62:bcff:fe28:a101%29','interface_index':29,
             'host_key_alias':'169.254.42.1','original_key_verified':True,'observed_new_boot':boot,
             'guard_path':guard,'postboot_USB_IRQ_protection_passed':True,'postboot_Image502_passed':True},
          'review_inputs': {key: str(root/key) for key in ('context','camera','probe_directory','capture_directory')},
          'files': {'key_transport': {'path':str(key_path),'sha256': review.sha(key_path.read_bytes())}}}
        request = host.make_request(tx, base, pins['update_worker']['sha256'], forward)
        save(out/'request-private.json', request); request_raw = (out/'request-private.json').read_bytes()
        (out/'stage-worker.py').write_bytes(worker_path.read_bytes())
        save(out/'binding-private.json', {'schema':'samurai-charger-reattach-binding-v1','transaction_id':tx,
             'request_sha256':review.sha(request_raw),'source_pins_sha256':review.sha((host.HERE/'source-pins.json').read_bytes()),
             'generated_from_actual_IRQ_adoption':True,'reviewed':base})
        identity = dict(ident, guard_sha256=base['guard_sha256'])
        def snapshot(t, new=False, paused=False, full=False):
            s = dict(valid=1,protection_ok=1,online=1,shadow=0,age_ms=0,error=0,stop_error=0,latched=0,fault=0,
                 source_inhibit=0,cycle_timeout=0,thermal_inhibit=0,flags=0,gauge_charge_stop=0,gauge_current_ua=10000,
                 logical_full=int(full),hold_requested=int(full),full_holding=int(full),full_cause=3 if full else 0,
                 desired_enable=int(not paused and not full),session_seconds=0 if full else 100,budget_ua=500000,
                 temp_decic=250,thermal_band=4,band_pre_shake=0,cell1_uv=4000000,cell2_uv=4000000,pack_uv=8000000)
            regs = {'00':10,'0f':10,'02':5,'04':104,'08':8 if paused else (0 if full else 16)}
            state = dict(boot_id=boot,release=worker.RELEASE,taint='0',driver='samurai-mp2650',camera_pm={str(i):'suspended' for i in range(4)},
                  m2m=json.dumps(dict(users=0,orphans=0,jobs=0,first_error=0,running=False,fatal=False,pinned=False)),
                  services=[dict(comm=name,pid=i+20,uid=10000) for i,name in enumerate(('phoc','phosh','pipewire','wireplumber'))],
                  registers=regs)
            return dict(state=state,sample=s,registers=regs,notes=dict(worker.NOTES,**{'samurai-mp2650':worker.NEW_NOTE if new else review.OLD_NOTE}),
                 source=dict(online='1',usb_type='Unknown [SDP] DCP CDP C',current_max='500000',input_current_limit='500000'),
                 openrc_started=True,limits=dict(native_ua=500000,source_budget_ua=500000,input_ua=500000,charge_ua=250000,cv_uv=4362500),
                 read_start=t,read_end=t+0.1,protection_health='Good',
                 protection=dict(id=0x2719,error=0,safety=0,pf=0,operation=0x300,manufacturing=0x18),
                 identity=identity,mac_evidence=dict(raw_base64=base64.b64encode(cached).decode(),sha256=cache_sha,
                     attribute_dev=1,attribute_inode=19,instance_inode=20))
        before, oldpaused, newpaused, after = snapshot(100), snapshot(101,paused=True), snapshot(102,new=True,paused=True), snapshot(103,new=True)
        remote_root = '/root/charging-management-20261023/' + tx
        argv = ['python3','-B',remote_root+'/stage-worker.py','--execute-stage']
        sup_argv = ['python3','-B',remote_root+'/stage-supervisor.py','--execute-supervisor']
        common = dict(transaction_id=tx,boot_id=boot,request_sha256=review.sha(request_raw))
        launch = dict(common,pid=123,start_ticks=234,argv=argv,supervisor_pid=121)
        sup = dict(common,pid=121,start_ticks=232,argv=sup_argv)
        term = {**{k:v for k,v in launch.items() if k!='start_ticks'},'terminal':True,'returncode':0}
        result = dict(schema='samurai-charger-reattach-update-result-v1',transaction_id=tx,request_sha256=review.sha(request_raw),
             passed=True,terminal=True,installed_new=True,native_usb_and_protection_kept_loaded=True,camera_services_unchanged=True,
             runtime_validation_pending=False,mutating_process_unknown=False,primary_error=None,stop_error=None,recovery_error=None,
             recovery_state=None,pending_child_pid=None,before_state='managed',accepted_state='managed',
             old_manifest_sha256=review.OLD,new_manifest_sha256=review.NEW,sample=after['sample'],limits=after['limits'],
             old_stopped_sample=oldpaused['sample'],new_inhibited_sample=newpaused['sample'],
             final_files={p:{'sha256':worker.HASHES[p],'mode':oct(mode)} for p,mode in worker.MODES.items()})
        raw = {'request-private.json':request_raw,'manifest.json.before':old_manifest,'samurai-mp2650.ko.before':old_ko}
        docs = {'process-private.json':dict(transaction_id=tx,boot_id=boot,pid=123,start_ticks=234,argv=argv),
             'worker-launch-receipt-private.json':launch,'worker-terminal-private.json':term,
             'supervisor-process-private.json':sup,'supervisor-terminal-private.json':dict(sup,terminal=True,worker_pid=123,worker_returncode=0,returncode=0),
             'launch-receipt-private.json':sup,'result.json':result,
             'before-private.json':{'observation':before,'modes':worker.MODES},'old-inhibited-private.json':oldpaused,
             'new-inhibited-private.json':newpaused,'after-private.json':after,
             'events-private.json':[['fresh-manager',worker.SERVICE_SHA],['manager-command',worker.SERVICE_SHA,'stop'],
                  ['process','rmmod','samurai_mp2650'],['process','insmod',worker.KO,'runtime_board=1','control=1'],
                  ['fresh-manager',worker.SERVICE_SHA],['manager-command',worker.SERVICE_SHA,'start']],
             'last-process-private.json':{'args':['insmod',worker.KO,'runtime_board=1','control=1'],'returncode':0,'stdout':'','stderr':''}}
        def write_fetch():
            for name, doc in docs.items(): raw[name] = (json.dumps(doc,indent=2)+'\n').encode()
            response = dict(transaction_id=tx,request_sha256=review.sha(request_raw),supervisor_receipt=docs['launch-receipt-private.json'],
                 worker_terminal_verified=True,worker_terminal=docs['worker-terminal-private.json'],worker_result=docs['result.json'],
                 process={'state':'absent'},supervisor_process={'state':'zombie'},
                 identity_observation={'boot_id':boot,'source_boot_same':True,'guard_matches':True},
                 identity_after={'boot_id':boot,'source_boot_same':True,'guard_matches':True},
                 files={name:{'bytes':len(value),'sha256':review.sha(value),'base64':base64.b64encode(value).decode()} for name,value in raw.items()})
            for name, data in raw.items():
                (call/'raw').mkdir(exist_ok=True); (call/'raw'/name).write_bytes(data)
            save(call/'stdout-private.json',response); save(call/'received-result-private.json',response)
            (call/'stderr-private.txt').write_bytes(b'')
            key = host.load(actual_host_pins['key_transport']['path'],'test_original_key_source')
            sshargv = [key.SSH,'-C','-6','-T',*key.OPTIONS,'-o','HostKeyAlias=169.254.42.1','root@fe80::62:bcff:fe28:a101%29','python3 -']
            save(call/'transport-child-private.json',{'pid':999,'argv':sshargv,'terminal':False})
            save(call/'transport-terminal-private.json',{'pid':999,'terminal':True,'returncode':0,'primary_error':None,'cleanup_errors':[]})
            envelope = dict(action='fetch',request=request,request_sha256=review.sha(request_raw),request_base64=base64.b64encode(request_raw).decode(),
                worker_base64=None,window_confirmed=False,supervisor_base64=None,supervisor_sha256=pins['update_supervisor']['sha256'])
            (call/'executed-remote.py').write_bytes(('STAGE_TRANSPORT='+repr(envelope)+'\n').encode()+values['update_remote'])
        def routed_load(path,name):
            if review.local(path)==host_path.resolve(): return host
            module = original_load(path,name)
            if review.local(path)==worker_path.resolve(): module.MAC_CACHE_SHA=cache_sha
            return module
        write_fetch()
        with patch.object(review,'load',side_effect=routed_load):
            checked = review.review_update(call,base)
            assert checked['runtime_expected']['notes']['samurai_mp2650']==review.NEW_NOTE
            assert checked['pointer']==base['pointer'] and checked['guard_path']==guard
            assert {k:v for k,v in checked['runtime_expected']['notes'].items() if k!='samurai_mp2650'} == {
                k:v for k,v in base['runtime_expected']['notes'].items() if k!='samurai_mp2650'}
            passed('actual saved fetch/host.bound/worker health chain yields only charger runtime overlay')
            docs['supervisor-terminal-private.json']['worker_returncode']=1; write_fetch()
            rejects('failed original supervisor/worker is not promoted',lambda:review.review_update(call,base))
            docs['supervisor-terminal-private.json']['worker_returncode']=0
            docs['result.json']['mutating_process_unknown']=True; write_fetch()
            rejects('unknown mutating child cannot yield overlay',lambda:review.review_update(call,base))
            docs['result.json']['mutating_process_unknown']=False
            docs['result.json']['before_state']='full_holding'; write_fetch()
            rejects('healthy Full preflight/refused update cannot yield overlay',lambda:review.review_update(call,base))
            docs['result.json']['before_state']='managed'
            docs['after-private.json']['notes']['samurai-mp2650']=review.OLD_NOTE; write_fetch()
            rejects('new disk with old resident charger rejected',lambda:review.review_update(call,base))
            docs['after-private.json']['notes']['samurai-mp2650']=review.NEW_NOTE
            docs['after-private.json']['mac_evidence']['attribute_inode']=999; write_fetch()
            rejects('same note with replaced protection kernfs instance rejected',lambda:review.review_update(call,base))
            docs['after-private.json']['mac_evidence']['attribute_inode']=19
            docs['after-private.json']['protection']['safety']=1; write_fetch()
            rejects('final protection error rejected by actual worker policy',lambda:review.review_update(call,base))
            docs['after-private.json']['protection']['safety']=0; write_fetch()
            other = copy.deepcopy(base); other['boot_id']='22222222-2222-4222-8222-222222222222'
            rejects('cross-boot/base adoption mismatch rejected',lambda:review.review_update(call,other))
            final = review.review_update(call,base)

            base_api = SimpleNamespace(review_adoption=lambda *a,**k:copy.deepcopy(base))
            with patch.object(review,'base_module',return_value=base_api), patch.object(launcher,'identity_review',return_value=review), \
                 patch.object(binder.m,'identity_review',return_value=review):
                migration=root/'migration.json'
                frozen=launcher.collector().FROZEN
                save(migration,dict(schema='charging-icon-irq-runtime-update-template-tests-v1',passed=True,
                     runtime_identity_unbound=True,manifest_sha256=launcher.MANIFEST,sha256=frozen,files={}))
                target=root/'bound'/'identity-pins-private.json'
                absent=root/'never-created'/'identity-pins-private.json'
                rejects('missing real update evidence refuses bind before mkdir',lambda:binder.bind('c','c','p','p',root/'absent',pins=absent,migration=migration))
                assert not absent.parent.exists()
                bound=binder.bind('c','c','p','p',call,pins=target,migration=migration)
                assert bound['bound_actual_runtime_update'] and launcher.runtime_expected(target)==final['runtime_expected']
                passed('actual binder and runtime profile consume completed overlay without changing base pointer')
                oldpins=json.loads(target.read_bytes()); oldpins['schema']='samurai-icon-irq-identity-v1'; save(target,oldpins)
                rejects('old IRQ-only pins refused by runtime profile',lambda:launcher.reviewed_identity(target))
                oldpins['schema']='samurai-icon-irq-runtime-update-v1';save(target,oldpins)
                capture_private=root/'capture'
                request_box={}
                def fake_ssh(command,**kw):
                    data=json.loads(kw['input']);request_box.update(data)
                    if data['action']=='launch':
                        reply={'launched':True,'launch_receipt':dict(data,pid=10,start_ticks=20)}
                    else:
                        receipt=dict(data,pid=10,start_ticks=20)
                        observations=[]
                        for t,tick in ((10,4),(11,5)):
                            observations.append({'remote_realtime':t,'remote_boottime':t,
                               'status':dict(pid=10,start_ticks=20,active=True,terminal=False,phase='ready',ready_for_user_action=True,
                                             realtime=t,remaining_boottime_seconds=300-t,tick=tick,t=t),
                               'process':{'state':'alive','pid':10,'start_ticks':20,'argv':data['argv']}})
                        reply={'identity_unchanged':True,'launch_receipt':receipt,'observations':observations,'clock_start':{'boot':0}}
                    return SimpleNamespace(returncode=0,stdout=json.dumps(reply).encode(),stderr=b'')
                launched=launcher.run('launch','charging-icon-runtime-fixture',True,ssh=fake_ssh,private=capture_private,pins=target,migration=migration)
                assert launched['launch_receipt_verified'] and request_box['manifest_sha256']==review.NEW and request_box['max_seconds']==300
                assert request_box['identity_expected']['notes']['samurai_mp2650']==review.NEW_NOTE
                status=launcher.run('status','charging-icon-runtime-fixture',ssh=fake_ssh,private=capture_private,pins=target,migration=migration)
                assert status['may_prompt_user'] and status['recheck_if_not_prompted_within_seconds']==3
                passed('original actual run/status uses new tuple with unchanged two-tick/130s/8s ready gate')
                transport=load(HERE/'transport.py','test_prevalidated_transport')
                callback=transport.prevalidated(final['endpoint'],json.loads(target.read_bytes())['transport_inputs'])
                with patch.object(transport.subprocess,'run',return_value=SimpleNamespace(returncode=0,check_returncode=lambda:None)) as called, \
                     patch.object(launcher,'identity_review',side_effect=AssertionError('local review inside timed callback')):
                    callback('read-only-synthetic-command',check=False)
                    assert called.call_args.args[0][1:4]==['-C','-6','-T']
                passed('actual prepared SSH callback does not repeat any local review inside timing')

    baseline = load(REF/pins['base_launcher']['path'],'test_unchanged_collector')
    original = (REF/pins['base_launcher']['path']).read_text()
    module=launcher.collector()
    import inspect
    for name in ('run','ready_check','retain_fetch','cleanup_check'):
        assert inspect.getsource(getattr(module,name))==inspect.getsource(getattr(baseline,name))
    for name in ('worker.py','audit.py','capture-entry.py','baseline-test-result.json'):
        assert (HERE/name).read_bytes()==(HERE.parent/'icon-capture-irq-cohort-candidate'/name).read_bytes()
    passed('original finite collector run/ready/fetch/cleanup bodies and worker/audit/entry/32 receipt exact')
    files={name:review.sha((HERE/name).read_bytes()) for name in
           ('launcher.py','update-review.py','bind-identity.py','transport.py','source-pins.json','test-profile.py')}
    result=dict(schema='charging-icon-irq-runtime-update-template-tests-v1',passed=True,
                runtime_identity_unbound=True,manifest_sha256=launcher.MANIFEST,sha256=baseline.FROZEN,files=files,
                tests_run=len(cases),cases=cases,old_matrices_rerun=False,device_accessed=False,
                fixture_scope='Temporary saved transaction; real functions, modelled source-loader/cache/device/SSH edges. No real runtime pins.')
    save(HERE/'template-test-result.json',result)
    print(json.dumps({'passed':True,'tests_run':len(cases),'device_accessed':False}))


if __name__=='__main__': main()
