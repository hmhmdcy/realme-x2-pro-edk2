"""New forward/inverse dispatch seam only; intercept before any transport."""
from pathlib import Path
import ast,base64,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('timer_dispatch_test',HERE/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);u=h.u
original_out=u.OUT;original_call=u.call
assert h.check()['passed']
captured=[]
def no_transport(label,code,readonly=True):
    tree=ast.parse(code)
    first=tree.body[0];assert isinstance(first,ast.Assign) and first.targets[0].id=='PACKET'
    packet=ast.literal_eval(first.value)
    assert not readonly and label=='launch'
    assert packet['root']==u.REMOTE and packet['boot_id']==u.request()['identity']['boot_id']
    inverse=base64.b64decode(packet['files']['rollback-two-files.tar.gz'],validate=True)
    assert u.sha(inverse)=='c72589194965a9a49af66b6c0032e196dd1407cd2defed2c193c432be718f38c'
    assert all(u.sha(base64.b64decode(raw))==packet['hashes'][name] for name,raw in packet['files'].items())
    assert base64.b64decode(packet['files']['stage-worker.py'])==(HERE/'stage-worker.py').read_bytes()
    captured.append(dict(label=label,inverse_sha256=u.sha(inverse),files=sorted(packet['files']),transport_started=False))
    return dict(intercepted=True)
try:
    with tempfile.TemporaryDirectory(prefix='samurai-timer-owned-dispatch-') as name:
        root=Path(name)
        for filename in ['request-private.json','stage-worker.py','previous-pointer.json']:
            (root/filename).write_bytes((original_out/filename).read_bytes())
        (root/'preflight').mkdir();(root/'preflight/reply.json').write_text(json.dumps(dict(passed=True,eligible=True)))
        u.OUT=root;u.call=no_transport
        assert h.launch()==dict(intercepted=True) and len(captured)==1
finally:u.OUT=original_out;u.call=original_call
for path in HERE.glob('*.py'):ast.parse(path.read_bytes())
result=dict(passed=True,cases=captured,only_dispatch_OS_boundary_modeled=True,phone_accessed=False,lease_created=False,launch_started=False,
            actual_rollback_pair_used=True,actual_same_child_supervisor_source_preserved=True)
with (HERE/'host-test-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,phone_accessed=False,transport_started=False)))
