"""Probe audit and exact original-supervisor dispatch, intercepted before SSH."""
from pathlib import Path
import ast,base64,copy,importlib.util,json,tempfile,time
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=load('timer_inverse_host_test',HERE/'host.py');u=h.u;m=h.worker()
fixture=load('timer_inverse_host_fixture',HERE/'test-source-fixture.py').make_fixture(m);raws=fixture['raws']
original_out=u.OUT;original_call=u.call
inverse=(original_out/'rollback-two-files.tar.gz').read_bytes()
identity=copy.deepcopy(m.SOURCE_IDENTITY);identity['boot_id']='77777777-8888-4999-aaaa-bbbbbbbbbbbb'
paths=m.source_paths(m.SOURCE_TX)
request=dict(schema='samurai-charger-timer-cold-rollback-request-v1',transaction_id=u.TX,profile=m.PROFILES[1],identity=identity,
 source_identity=m.SOURCE_IDENTITY,source_stage=dict(transaction_id=m.SOURCE_TX,evidence={name:dict(path=paths[name],sha256=u.sha(raw)) for name,raw in raws.items()}),
 current_cache=copy.deepcopy(fixture['post']['raw']['protection_cache_after']),payload_sha256=m.ROLLBACK_PAYLOAD,payload_base64=base64.b64encode(inverse).decode(),
 worker_sha256=u.sha((HERE/'restore-worker.py').read_bytes()),lease_token='a'*48)
observation=dict(state='source_boot_ended',source_boot_id=m.SOURCE_IDENTITY['boot_id'],current_boot_id=identity['boot_id'])
observed={role:copy.deepcopy(observation) for role in ['worker','supervisor']}
current=dict(identity=identity,release=m.RELEASE,machine='aarch64',taint='0',boot=dict(bytes=100663296,sha256=m.BOOT),
 logdump=dict(bytes=67108864,sha256=m.LOGDUMP504),notes=m.NEW_NOTES,module_states={name:'live' for name in m.NEW_NOTES},current_cache=request['current_cache'])
snapshot=copy.deepcopy(json.loads(raws['before']));now=time.clock_gettime(time.CLOCK_BOOTTIME)
snapshot.update(notes=copy.deepcopy(m.NEW_NOTES),current_cache=copy.deepcopy(request['current_cache']),read_start=now-.001,read_end=now,
                limits=dict(input_ua=500000,charge_ua=250000,cv_pack_uv=8725000))
snapshot['state']['boot_id']=identity['boot_id']
reply=dict(passed=True,eligible=True,read_only=True,phone_directory_or_lease_created=False,request=request,current=current,snapshot=snapshot,
           source_process_observations=observed,source_proof=m.verify_source_records(request,raws,observed),
           source_raws={name:dict(sha256=u.sha(raw),base64=base64.b64encode(raw).decode()) for name,raw in raws.items()})
assert h.audit_probe(reply)==request
wrong=copy.deepcopy(reply);wrong['snapshot']['current_cache']['instance_inode']+=1
try:h.audit_probe(wrong)
except AssertionError:pass
else:raise AssertionError('host accepted changed cache instance')
captured=[]
def no_transport(label,code,readonly=True):
    tree=ast.parse(code);first=tree.body[0]
    assert isinstance(first,ast.Assign) and first.targets[0].id=='PACKET' and label=='launch' and not readonly
    packet=ast.literal_eval(first.value)
    assert packet['root']==u.REMOTE and packet['boot_id']==identity['boot_id'] and packet['request']==request
    decoded={name:base64.b64decode(value,validate=True) for name,value in packet['files'].items()}
    assert all(u.sha(raw)==packet['hashes'][name] for name,raw in decoded.items())
    assert decoded['rollback-two-files.tar.gz']==inverse and decoded['restore-worker.py']==(HERE/'restore-worker.py').read_bytes()
    assert decoded['supervisor.py']==(u.POST/'pm-smoke-supervisor.py').read_bytes()
    wrapper=ast.parse(decoded['worker.py'])
    argv=next(n for n in wrapper.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=='argv')
    assert ast.literal_eval(argv.value)==['restore','--execute-rollback']
    call=wrapper.body[-1].value
    assert isinstance(call,ast.Call) and call.func.attr=='run_path' and ast.literal_eval(call.args[0])==u.REMOTE+'/restore-worker.py'
    captured.append(dict(correct_current_identity=True,exact_inverse=True,original_same_child_supervisor=True,only_restore_entrypoint=True,transport_started=False))
    return dict(intercepted=True)
try:
    with tempfile.TemporaryDirectory(prefix='samurai-timer-inverse-dispatch-') as name:
        root=Path(name);u.OUT=root;u.call=no_transport
        (root/'restore-worker.py').write_bytes((HERE/'restore-worker.py').read_bytes())
        (root/'request-private.json').write_text(json.dumps(request,indent=2)+'\n')
        (root/'preflight').mkdir();(root/'preflight/reply.json').write_text(json.dumps(reply))
        assert h.launch()==dict(intercepted=True) and len(captured)==1
finally:u.OUT=original_out;u.call=original_call
parameters={key:request[key] for key in ['transaction_id','worker_sha256','lease_token','payload_base64']}
source=h.probe_source(parameters);ast.parse(source)
assert b"if __name__=='__main__':raise SystemExit(main())" not in source
assert b'flock(device.lock,fcntl.LOCK_SH|fcntl.LOCK_NB)' in source and b'device.begin(' not in source[source.index(b'def rollback_probe('):]
result=dict(passed=True,modeled_probe_audit_and_cache_rejection=True,dispatch=captured,
            probe_source_parsed_no_main_or_mutating_begin=True,phone_accessed=False,lease_created=False,transport_started=False)
with (HERE/'host-test-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,phone_accessed=False,transport_started=False)))
