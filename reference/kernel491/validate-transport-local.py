"""Finite491 host transport contracts; only a local helper and inert stub transport."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import base64, copy, hashlib, importlib.util, io, json, subprocess, sys, tarfile, traceback, types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel491')
TEMPLATE = PRIVATE/'k491-package-only-r1-offline-template-r1'
digest = lambda data: hashlib.sha256(data).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('guard461_transport491_local',HERE.parent/'kernel461/storage.py')
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    guard.mount.mounted_build()  # root + original guard; no user/lock fallback.
    number = 1
    while (PRIVATE/f'transport-local-{number:03d}').exists(): number += 1
    work = PRIVATE/f'transport-local-{number:03d}'; work.mkdir(mode=0o700)
    report = dict(stage=491,passed=False,scope='local compressed-query decode/compile and fixture-only host transport checks',
                  private_attempt=work.name,real_ssh_or_device_or_sdk_accessed=False,
                  real_transport_module_imported=False,query_executed=False,full_real_ssh_argv_checked=False)
    try:
        host_source = (HERE/'host-run.py').read_bytes()
        namespace = {'__name__':'host491_local_contract','__file__':str(HERE/'host-run.py')}
        exec(compile(host_source,str(HERE/'host-run.py'),'exec'),namespace)
        host = types.SimpleNamespace(**namespace)
        report['source_sha256'] = {'host-run.py':digest(host_source),'validate-transport-local.py':digest(Path(__file__).read_bytes())}
        prepared = json.loads((TEMPLATE/'preparation-private.json').read_bytes())
        source = (TEMPLATE/'stage-query.py').read_bytes()
        assert not prepared['deployable'] and digest(source)==prepared['query_sha256']['stage']
        command, encoded = host.encode_stage(source)
        helper = "import base64,zlib,hashlib,sys;s=zlib.decompress(base64.b85decode(sys.argv[1]));assert hashlib.sha256(s).hexdigest()==sys.argv[2];compile(s,'<local-compile-only>','exec');sys.stdout.buffer.write(s)"
        argv = [sys.executable,'-B','-c',helper,encoded,digest(source)]
        result = subprocess.run(argv,capture_output=True,timeout=10)
        (work/'roundtrip-stdout-private.bin').write_bytes(result.stdout)
        (work/'roundtrip-stderr-private.bin').write_bytes(result.stderr)
        assert result.returncode==0 and result.stdout==source and result.stderr==b''
        assert len(command.encode())<24000 and sum(len(value.encode())+1 for value in argv)<24000
        report['actual_template_roundtrip'] = dict(query_sha256=digest(source),query_bytes=len(source),
            compressed_ssh_command_bytes=len(command.encode()),local_helper_argv_bytes=sum(len(value.encode())+1 for value in argv),
            helper_exit_code=0,decoded_query_byte_identical=True,query_compiled_not_executed=True)

        transport = work/'stub-transport.py'
        transport.write_text("from subprocess import CompletedProcess,TimeoutExpired\nMODE='success'\ncalls=[]\ndef raw_ssh(command,*,input,timeout,check):\n calls.append((command,input,timeout,check))\n if MODE=='timeout': raise TimeoutExpired('local-stub',timeout,output=b'\\x00partial\\xff',stderr=b'\\x80warning\\n')\n return CompletedProcess(command,0,b'\\x00success\\xff',b'\\x80stderr\\n')\n")
        transport_sha = digest(transport.read_bytes())
        now = datetime.now(timezone.utc)
        used = []
        mode = {'value':'success'}
        def loader(path,data):
            assert path==transport and digest(data)==transport_sha
            module = host.load_transport(path,data); module.MODE=mode['value']; used.append(module)
            return module
        def perform(bound,action,claimed=transport_sha):
            return host.perform(bound,action,transport,claimed,now=now,guard=lambda:None,loader=loader)
        def calls(): return sum(len(module.calls) for module in used)
        def fixture(name, age=0):
            parent = work/name; parent.mkdir(); bound=parent/'bound';bound.mkdir()
            stamp = (now-timedelta(seconds=age)).isoformat(); window='k491-package-only-r1'; preflight='k476-control-delay-r4'
            owner = dict(issued_at_utc=stamp,authorized_window_ids=[preflight,window],released=True,original_key_verified=True,
                charging_worker_exited=True,no_concurrent_owner=True,from_owner='charging',to_owner='camera',
                boot_guard_path='/fixture-only/guard',boot_id='fixture-only-boot',charging_manifest_sha256='fixture-manifest')
            scoped=copy.deepcopy(owner);scoped['authorized_window_ids']=[preflight]
            handoff=dict(issued_at_utc=stamp,fresh_preflight_verified=True,window_owner='camera',window_id=preflight,
                boot_guard_path='/fixture-only/guard',charging={'manifest_sha256':'fixture-manifest'},
                host_transport={'path':str(transport),'sha256':transport_sha})
            authorization={}
            for key,value in [('handoff',handoff),('owner',owner),('scoped_owner',scoped)]:
                path=parent/(key+'-fixture-private.json');path.write_text(json.dumps(value)+'\n');authorization[str(path)]=digest(path.read_bytes())
            worker=b'def main():\n    return 0\n';(bound/'worker.py').write_bytes(worker)
            source_hashes={name:digest((HERE/name).read_bytes()) for name in host.SOURCES}
            candidate_sha=digest((HERE.parent/'kernel490/candidate-state.json').read_bytes())
            plan=dict(stage=491,window_id=window,target_root='/var/lib/samurai/'+window,preflight_window_id=preflight,
                deployable=True,source_sha256=source_hashes,candidate_state_sha256=candidate_sha,payload_sha256={'worker.py':digest(worker)},
                modules_or_private_profiles_replaced=False,persistent_repository_created=False,candidate_retained=False,
                authorization_files_sha256=authorization,handoff=handoff,owner=owner,scoped_owner=scoped)
            (bound/'plan-private.json').write_text(json.dumps(plan)+'\n')
            with tarfile.open(bound/'payload-private.tar.gz','w:gz') as archive:
                for filename in ['worker.py','plan-private.json']:
                    data=(bound/filename).read_bytes();item=tarfile.TarInfo(filename);item.size=len(data);item.mode=0o600;archive.addfile(item,io.BytesIO(data))
            queries={}
            for action in sorted(host.ACTIONS):
                data=('# local fixture '+action+'; never executed\nraise RuntimeError("fixture must never execute")\n').encode()
                (bound/(action+'-query.py')).write_bytes(data);queries[action]=digest(data)
            payload=(bound/'payload-private.tar.gz').read_bytes()
            record=dict(stage=491,prepared=True,deployable=True,files=2,source_sha256=source_hashes,
                candidate_state_sha256=candidate_sha,worker_sha256=digest(worker),plan_sha256=digest((bound/'plan-private.json').read_bytes()),
                archive_bytes=len(payload),archive_sha256=digest(payload),query_sha256=queries)
            (bound/'preparation-private.json').write_text(json.dumps(record)+'\n')
            return bound
        def refuse(name,bound,action='stage',claimed=transport_sha):
            before=(len(used),calls())
            try: perform(bound,action,claimed)
            except (AssertionError,FileExistsError,FileNotFoundError,KeyError) as failure:
                (work/(name+'-expected-refusal-private.txt')).write_text(traceback.format_exc())
            else: raise AssertionError('Expected pre-transport rejection: '+name)
            assert (len(used),calls())==before
            report.setdefault('pre_transport_rejections',[]).append(name)
        refuse('actual-unbound-template',TEMPLATE)
        refuse('stale-owner',fixture('stale-owner',age=481))
        refuse('future-owner',fixture('future-owner',age=-1))
        bound=fixture('source-drift')
        plan=json.loads((bound/'plan-private.json').read_bytes());record=json.loads((bound/'preparation-private.json').read_bytes())
        plan['source_sha256']['owner-gate.py']='0'*64;record['source_sha256']=plan['source_sha256']
        (bound/'plan-private.json').write_text(json.dumps(plan)+'\n');record['plan_sha256']=digest((bound/'plan-private.json').read_bytes())
        (bound/'preparation-private.json').write_text(json.dumps(record)+'\n');refuse('source-drift',bound)
        for name,filename in [('query-hash','stage-query.py'),('worker-hash','worker.py'),('plan-hash','plan-private.json'),('payload-hash','payload-private.tar.gz')]:
            bound=fixture(name);(bound/filename).write_bytes((bound/filename).read_bytes()+b'\n');refuse(name,bound)
        refuse('transport-cli-sha',fixture('transport-cli-sha'),claimed='0'*64)
        bound=fixture('preexisting-stage');logs=bound.parent/'transport-k491-package-only-r1';logs.mkdir();(logs/'stage-attempt-private.json').write_bytes(b'prior-attempt\n')
        refuse('preexisting-stage',bound)

        bound=fixture('successful-stage-launch');before=calls();record=perform(bound,'stage');assert calls()==before+1
        sent=used[-1].calls[0];assert sent[1]==(bound/'payload-private.tar.gz').read_bytes() and sent[2:]==(70,False)
        assert record['command_bytes']<24000 and record['transport_completed'] and not record['target_state_unknown']
        refuse('duplicate-stage',bound)
        before=calls();record=perform(bound,'launch');assert calls()==before+1
        assert used[-1].calls[0][0]=='python3 -B -' and used[-1].calls[0][1]==(bound/'launch-query.py').read_bytes()
        refuse('duplicate-launch',bound,action='launch')
        report['successful_stateful_sends']=dict(stage_calls=1,launch_calls=1,duplicate_sends_blocked=True)
        bound=fixture('preexisting-launch');perform(bound,'stage');logs=bound.parent/'transport-k491-package-only-r1';(logs/'launch-attempt-private.json').write_bytes(b'prior-attempt\n')
        refuse('preexisting-launch',bound,action='launch')

        bound=fixture('timeout-stage');mode['value']='timeout';before=calls()
        try: perform(bound,'stage')
        except RuntimeError:
            (work/'timeout-expected-error-private.txt').write_text(traceback.format_exc())
        else: raise AssertionError('Timeout must remain unknown')
        assert calls()==before+1
        logs=bound.parent/'transport-k491-package-only-r1'
        assert (logs/'stage-stdout-private.bin').read_bytes()==b'\x00partial\xff'
        assert (logs/'stage-stderr-private.bin').read_bytes()==b'\x80warning\n'
        record=json.loads((logs/'stage-result-private.json').read_bytes());assert not record['transport_completed'] and record['target_state_unknown']
        refuse('timeout-stage-no-resend',bound);refuse('timeout-stage-no-launch',bound,action='launch')
        mode['value']='success'
        diagnostic=fixture('expired-diagnostics',age=86400)
        for action in ['observe','collect','observe']:
            before=calls();record=perform(diagnostic,action);assert calls()==before+1
            assert used[-1].calls[0][0]=='python3 -B -' and used[-1].calls[0][1]==(diagnostic/(action+'-query.py')).read_bytes()
            result_path=Path(record['result_private']);prefix=result_path.name.removesuffix('-result-private.json')
            extension='.tar.gz' if action=='collect' else '.bin'
            assert (result_path.parent/(prefix+'-stdout-private'+extension)).read_bytes()==b'\x00success\xff'
            assert (result_path.parent/(prefix+'-stderr-private.bin')).read_bytes()==b'\x80stderr\n'
        report.update(timeout_partial_bytes_preserved=True,timeout_stateful_resend_and_launch_blocked=True,
            expired_original_window_observe_collect_allowed=True,diagnostic_input_uses_only_action_query=True,
            collect_stdout_binary_preserved=True,stub_raw_ssh_calls=calls(),stub_imports=len(used))
        assert report['source_sha256']['host-run.py']==digest((HERE/'host-run.py').read_bytes())
        report['passed']=True
    except BaseException:
        report['failure']=traceback.format_exc();(work/'unexpected-failure-private.txt').write_text(report['failure'])
    path=work/'result-private.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=491,passed=report['passed'],private_report=str(path),report_sha256=digest(path.read_bytes()))))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
