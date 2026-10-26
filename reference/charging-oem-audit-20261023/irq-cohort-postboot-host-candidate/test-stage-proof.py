"""New saved-stage authentication boundaries only; no old suite or transport."""
from pathlib import Path, PurePosixPath
import base64
import copy
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value, indent=2) + '\n').encode()


def main():
    spec = importlib.util.spec_from_file_location('actual_stage_proof', HERE / 'stage-proof.py')
    p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
    pins, host, worker, key = p.modules()
    cases = []
    def rejected(name, call):
        try: call()
        except (ValueError, RuntimeError, FileNotFoundError, KeyError): cases.append(dict(name=name, passed=True))
        else: raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix='samurai-irq-stage-proof-') as temp:
        tmp = Path(temp)
        tx = 'usb-irq-protection-stage-proof-test-001'
        stage = tmp / tx; stage.mkdir()
        fetched = stage / 'fetch-0123456789abcdef-private'; fetched.mkdir()
        (fetched / 'raw').mkdir()
        adoption_dir = tmp / 'adoption'; adoption_dir.mkdir()
        d = dict(transaction_id=host.ADOPTION_TX, guard=host.GUARD, candidate_boot_sha256=host.BOOT,
            candidate_logdump_sha256=host.LOGDUMP, manifest=host.R8, version=host.VERSION,
            boot='12345678-1234-4123-8123-123456789abc', old_boot='22345678-1234-4123-8123-123456789abc',
            serial_sha256='1' * 64, compatible_sha256=sha(b'realme,samurai\0'), rootfs='3' * 64,
            postboot_raw_sha256='4' * 64)
        pointer = dict(guard_path=host.GUARD, original_key_verified=True, baseline481_verified=True,
            charging_manifest_sha256=host.R8, candidate_boot_sha256=host.BOOT,
            candidate_logdump_sha256=host.LOGDUMP, Image502_verified=True, postboot_raw_sha256=d['postboot_raw_sha256'])
        endpoint = dict(kind='usb-ipv6', peer=host.PEER, interface_index=29, host_key_alias=host.ALIAS,
            original_key_verified=True, observed_new_boot=d['boot'], guard_path=host.GUARD, postboot_Image502_passed=True)
        source = dict(context={}, postboot={}, receiver={}, pointer=pointer, request=d,
            result=dict(passed=True, guard_created=True, old_pointer_backup_preserved=True, old_guards_preserved=True, pointer=pointer),
            endpoint=endpoint, reply=dict(guard_created=True, old_guards_preserved=True, transaction_id=host.ADOPTION_TX,
                boot_id=d['boot'], guard=host.GUARD, boot_and_logdump_verified=True, postboot_raw_sha256=d['postboot_raw_sha256'],
                fresh_validation_passed=True, charging_controls_written=False),
            terminal=dict(pid=20, terminal=True, returncode=0))
        paths = {}
        for name, value in source.items():
            path = adoption_dir / (('adoption-pointer-private.json' if name == 'pointer' else name + '.json'))
            path.write_bytes(encode(value)); paths[name] = path
        paths['executed'] = adoption_dir / 'executed.py'; paths['executed'].write_bytes(b'actual-old-adoption-boundary-is-fake\n')
        inputs, values = host.source_check()
        request = host.make_request(tx, d, pins['stage_worker']['sha256'], values['cohort_payload'])
        request_raw = encode(request); (stage / 'request-private.json').write_bytes(request_raw)
        worker_raw = Path(host.local(inputs['worker']['path'])).read_bytes()
        supervisor_raw = Path(host.local(inputs['supervisor']['path'])).read_bytes()
        remote_raw = Path(host.local(inputs['remote']['path'])).read_bytes()
        (stage / 'stage-worker.py').write_bytes(worker_raw)
        binding = dict(transaction_id=tx, request_sha256=sha(request_raw), endpoint=endpoint,
            source_pins_sha256=sha((Path(host.__file__).parent / 'source-pins.json').read_bytes()),
            evidence={name:dict(path=str(path), sha256=sha(path.read_bytes())) for name,path in paths.items()})
        # The retained actual pointer is read; this deliberately absent global
        # path must never be created or needed for retrospective source review.
        binding['evidence']['pointer']['path'] = str(tmp / 'nonexistent-current-pointer.json')
        (stage / 'binding-private.json').write_bytes(encode(binding))
        argv = [key.SSH, '-6', '-T', *key.OPTIONS, '-o', 'HostKeyAlias=' + host.ALIAS, 'root@' + host.PEER, 'python3 -']
        def code(action):
            envelope = dict(action=action, request=request, request_sha256=sha(request_raw),
                request_base64=base64.b64encode(request_raw).decode(), window_confirmed=action=='launch',
                supervisor_sha256=sha(supervisor_raw),
                worker_base64=base64.b64encode(worker_raw).decode() if action=='launch' else None,
                supervisor_base64=base64.b64encode(supervisor_raw).decode() if action=='launch' else None)
            return ('STAGE_TRANSPORT='+repr(envelope)+'\n').encode()+remote_raw
        launch = stage / 'launch-transport-private'; launch.mkdir()
        launch_code = code('launch'); (launch / 'executed-remote.py').write_bytes(launch_code)
        (fetched / 'executed-remote.py').write_bytes(code('fetch'))
        (stage / 'launch-intent-private.json').write_bytes(encode(dict(transaction_id=tx, request_count=1,
            argv=argv, request_sha256=sha(request_raw), code_sha256=sha(launch_code))))
        for directory, pid in ((launch,100),(fetched,101)):
            (directory / 'transport-child-private.json').write_bytes(encode(dict(pid=pid,argv=argv,terminal=False)))
            (directory / 'transport-terminal-private.json').write_bytes(encode(dict(pid=pid,terminal=True,returncode=0,primary_error=None,cleanup_errors=[])))
        root = p.REMOTE_ROOT + '/' + tx
        sup_argv=['python3','-B',root+'/stage-supervisor.py','--execute-supervisor']
        worker_argv=['python3','-B',root+'/stage-worker.py','--execute-stage']
        common=dict(transaction_id=tx,boot_id=d['boot'],request_sha256=sha(request_raw))
        sup=dict(common,pid=300,start_ticks=10,argv=sup_argv)
        worker_launch=dict(common,pid=301,start_ticks=11,argv=worker_argv,supervisor_pid=300)
        worker_terminal=dict(common,pid=301,argv=worker_argv,supervisor_pid=300,terminal=True,returncode=0)
        evidence=dict(supervisor_launch=sup,supervisor_process=sup,
            supervisor_terminal=dict(sup,terminal=True,returncode=0,worker_pid=301,worker_returncode=0),
            worker_launch=worker_launch,worker_terminal=worker_terminal,
            worker_process=dict(pid=301,start_ticks=11,argv=worker_argv,worker_sha256=request['worker_sha256'],transaction_id=tx,boot_id=d['boot']))
        sample={k:0 for k in ['shadow','error','stop_error','latched','fault','source_inhibit','cycle_timeout',
            'thermal_inhibit','gauge_charge_stop','flags','logical_full','hold_requested','full_holding','full_cause']}
        sample.update(valid=1,protection_ok=1,online=1,age_ms=5,session_seconds=10,temp_decic=265,thermal_band=4,
            desired_enable=1,budget_ua=500000,pack_uv=8600000,cell1_uv=4300000,cell2_uv=4300000)
        before=dict(read_start=99.5,read_end=99.8,sample=sample,state=dict(boot_id=d['boot'],release=worker.RELEASE,
            taint='0',driver='samurai-mp2650',registers={'00':10,'01':0,'02':5,'03':0,'04':0x68,'05':0,'07':0,'08':0x10,'09':0,'0f':10,'13':2},
            camera_pm={str(i):'suspended' for i in range(4)},m2m=json.dumps(dict(users=0,orphans=0,jobs=0,first_error=0,running=False,fatal=False,pinned=False)),
            services=[dict(pid=i+10,comm=n,uid=10000) for i,n in enumerate(['phoc','phosh','pipewire','wireplumber'])]),
            source=dict(online='1',usb_type='[SDP]',current_max='500000',input_current_limit='500000'),
            limits=dict(input_ua=500000,charge_ua=250000,cv_pack_uv=8725000),notes=worker.OLD_NOTES,
            openrc_started=True,protection_health='Good',protection=dict(id=0x2719,error=0,safety=0,pf=0,operation=0x300,manufacturing=0x18))
        stopped=copy.deepcopy(before);stopped.update(read_start=100,read_end=100.2)
        stopped['state']['registers']['08']=8;stopped['sample']['desired_enable']=0
        after=copy.deepcopy(stopped);after.update(read_start=100.3,read_end=100.5)
        result=dict(schema='samurai-usb-irq-protection-stage-result-v1',transaction_id=tx,cohort_delivery_sha256=worker.COHORT,
            payload_sha256=worker.PAYLOAD,old_manifest_sha256=worker.OLD,new_manifest_sha256=worker.NEW,
            phase='staged',status='staged/runtime_pending',staged=True,runtime_pending=True,terminal=True,
            disk_state='all_new_fsynced',stop_verified=True,primary_error=None,unknown_write_state=False,
            source_boot_id=d['boot'],source_version=worker.VERSION,source_guard_path=host.GUARD,
            activation_attempted=False,new_module_loaded=False,capture_issued=False,automatic_rollback_or_replay=False,
            stop_error=None,old_resident_notes=worker.OLD_NOTES,resident_notes_expected=worker.OLD_NOTES,
            adoption_fresh_validation_sha256='6'*64,
            final_files={t:dict(sha256=worker.NEW_FILES[t],mode='0o600',classification='new',old_sha256=worker.OLD_FILES[t],new_sha256=worker.NEW_FILES[t]) for t in worker.ORDER},
            temporary_files={t:dict(path=str(PurePosixPath(t).with_name('.'+PurePosixPath(t).name+'.'+tx+'.next')),state='absent') for t in worker.ORDER})
        evidence.update(before=before,stopped=stopped,after=after,result=result,
            adoption_proof=dict(actual_fresh_validation_sha256='6'*64,postboot_raw_sha256=d['postboot_raw_sha256'],guard_sha256=request['adoption']['guard_sha256']))
        files={Path(p.EVIDENCE[name]).name:encode(value) for name,value in evidence.items()}
        files['request-private.json']=encode({k:v for k,v in request.items() if k!='payload_base64'})
        import io,tarfile
        # Reuse exact cached rollback bytes, not invented old ko contents.
        cohort_result=json.loads(values['cohort_payload_result'])
        rollback_path=host.local(cohort_result['output'])/'rollback-r8-payload.tar.gz'
        with tarfile.open(rollback_path,'r:gz') as tar:
            for member in tar.getmembers(): files[Path(member.name).name+'.before']=tar.extractfile(member).read()
        def publish():
            for name,raw in files.items(): (fetched/'raw'/name).write_bytes(raw)
            response=dict(transaction_id=tx,request_sha256=sha(request_raw),worker_result=json.loads(files['result.json']),
                worker_terminal_verified=True,worker_terminal=json.loads(files['worker-terminal-private.json']) if 'worker-terminal-private.json' in files else None,
                process=dict(state='absent',pid=301),supervisor_process=dict(state='absent',pid=300),
                files={n:dict(bytes=len(r),sha256=sha(r),base64=base64.b64encode(r).decode()) for n,r in files.items()})
            (fetched/'stdout-private.json').write_bytes(encode(response));(fetched/'received-result-private.json').write_bytes(encode(response))
        publish()
        # Only the already-tested old full-502 review/transport identity boundary
        # is fake. All new source/request/receipt/raw/chain/state checks execute.
        old_adoption=SimpleNamespace(review=lambda *a:(d,{}),payload=lambda *a:paths['executed'].read_bytes())
        with patch.object(p,'modules',return_value=(pins,host,worker,key)), patch.object(host,'PRIVATE',tmp), patch.object(host,'load_module',return_value=old_adoption):
            reviewed=p.review_stage(stage,fetched,expected_transaction=tx)
            projection=p.guard_stage_fields(reviewed)
            assert len(projection)==7 and len(projection['evidence'])==14 and reviewed['identity']==request['identity']
            assert projection['evidence']['worker_source']['path']==root+'/stage-worker.py'
            assert reviewed['evidence']['worker_source']['origin']=='uploaded-source-bound-by-executed-remote'
            cases.append(dict(name='complete saved chain and normalized 7/14 projection',passed=True))
            mutations=[('worker nonzero terminal','worker-terminal-private.json','returncode',1),
                ('wrong Popen PID','worker-launch-receipt-private.json','pid',302),
                ('supervisor unknown terminal','supervisor-terminal-private.json','terminal',False),
                ('boolean exit code is not an integer terminal','worker-terminal-private.json','returncode',False),
                ('wrong worker start ticks','process-private.json','start_ticks',12),
                ('stage passed label with failed disk state','result.json','disk_state','partial_known'),
                ('stage passed label with primary error','result.json','primary_error',{'error':'injected'})]
            for name,file,key_,value in mutations:
                original=files[file];changed=json.loads(original);changed[key_]=value;files[file]=encode(changed);publish()
                rejected(name,lambda:p.review_stage(stage,fetched));files[file]=original;publish()
            original=files['after-private.json'];changed=json.loads(original);changed['state']['registers']['08']=0x10
            files['after-private.json']=encode(changed);publish();rejected('passed result cannot mask CHG enabled after stage',lambda:p.review_stage(stage,fetched))
            files['after-private.json']=original;publish()
            target=fetched/'raw'/'process-private.json';original=target.read_bytes();target.write_bytes(b'{}')
            rejected('raw copy differs from authenticated fetch response',lambda:p.review_stage(stage,fetched));target.write_bytes(original)
            executable=fetched/'executed-remote.py';original=executable.read_bytes();executable.write_bytes(original+b'\n# changed\n')
            rejected('different executed fetch source',lambda:p.review_stage(stage,fetched));executable.write_bytes(original)
            rejected('different expected stage transaction',lambda:p.review_stage(stage,fetched,expected_transaction=tx+'x'))
            missing=files.pop('worker-terminal-private.json');publish()
            rejected('missing actual Popen terminal despite stage success',lambda:p.review_stage(stage,fetched))
            files['worker-terminal-private.json']=missing;publish()
    result=dict(passed=True,cases=cases,count=len(cases),actual_new_functions=True,
        old_full_Image502_review_and_transport_boundaries_fake=True,synthetic_saved_stage_only=True,
        actual_stage_or_future_request_created=False,old_suites_rerun=False,device_or_transport_accessed=False,
        files={n:sha((HERE/n).read_bytes()) for n in ['stage-proof.py','stage-source-pins.json','test-stage-proof.py']})
    (HERE/'stage-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,count=len(cases))))


if __name__=='__main__': main()
