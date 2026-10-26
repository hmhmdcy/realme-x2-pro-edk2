"""Reuse the completed forward-stage filesystem/OS fixture; no phone access."""
from pathlib import Path
import ast,base64,copy,hashlib,json
HERE=Path(__file__).resolve().parent
def make_fixture(m):
    test=HERE.parent/'charge-timer-cold-update/test-lifecycle.py'
    source=test.read_text();tree=ast.parse(source)
    index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='failure')
    scope=dict(__file__=str(test),__name__='forward_fixture_only')
    exec(compile(ast.Module(body=tree.body[:index],type_ignores=[]),'<same-forward-fixture-setup>','exec'),scope)
    captured={}
    def capture(scope):
        root=scope['root'];evidence=root/'evidence';request=scope['request'];base=scope['BASE']
        request_raw=(base/'charge-timer-cold-update-live-20261024-01/request-private.json').read_bytes()
        wrapper=("import io,sys,runpy\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr(request_raw)+"))\nsys.argv=['stage','--execute-stage']\nrunpy.run_path("+repr(m.ROOT+'/'+m.SOURCE_TX+'/stage-worker.py')+",run_name='__main__')\n").encode()
        supervisor=(HERE.parent/'irq-native-usb-pm-postboot-host-candidate/pm-smoke-supervisor.py').read_bytes()
        worker_process=dict(pid=654321,startticks=200,argv=['/usr/sbin/python3','-B',m.ROOT+'/'+m.SOURCE_TX+'/worker.py'])
        supervisor_process=dict(pid=654320,startticks=190,argv=['/usr/sbin/python3','-B',m.ROOT+'/'+m.SOURCE_TX+'/supervisor.py','--supervise',m.ROOT+'/'+m.SOURCE_TX])
        encode=lambda value:(json.dumps(value,indent=2)+'\n').encode()
        raws=dict(request=request_raw,stage_source=scope['source'],wrapper=wrapper,supervisor=supervisor,
                  launch=encode(dict(boot_id=m.SOURCE_IDENTITY['boot_id'],worker_sha256=m.STAGE_WRAPPER)),
                  supervisor_launch=encode(supervisor_process),supervisor_process=encode(supervisor_process),worker_process=encode(worker_process),
                  worker_terminal=encode(dict(pid=worker_process['pid'],process=worker_process,terminal=True,returncode=0,receipt_error=None)),
                  stage_process=encode(dict(pid=worker_process['pid'],start_ticks=worker_process['startticks'],argv=worker_process['argv'],boot_id=m.SOURCE_IDENTITY['boot_id'],transaction_id=m.SOURCE_TX)))
        for name,filename in {'result':'result.json','before':'before-private.json','stopped':'stopped-private.json','after':'after-private.json',
                              'files_before':'files-before-private.json','old_charger':'samurai-mp2650.ko.before','old_manifest':'manifest.json.before'}.items():
            raws[name]=(evidence/filename).read_bytes()
        captured.update(raws=raws,artifacts=scope['artifacts'],forward_files=scope['files'],post=scope['post'])
    scope['_capture_fixture']=capture
    loop=copy.deepcopy(tree.body[index]);loop.iter=ast.List(elts=[ast.Constant(value=None)],ctx=ast.Load())
    with_node=next(n for n in loop.body if isinstance(n,ast.With))
    # The old fixture reused a historical state() envelope. This OS-boundary
    # correction makes its modeled boot agree with the current request too.
    device_class=next(n for n in with_node.body if isinstance(n,ast.ClassDef) and n.name=='Device')
    observe=next(n for n in device_class.body if isinstance(n,ast.FunctionDef) and n.name=='observe')
    observe.body.insert(-1,ast.parse("value['state']['boot_id']=request['identity']['boot_id']").body[0])
    with_node.body.append(ast.parse('_capture_fixture(globals())').body[0])
    module=ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[]))
    exec(compile(module,'<same-forward-stage-real-filesystem-fixture>','exec'),scope)
    return captured
