"""Extract only actual read-only identity/carrier/note code. No runtime binding."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    raw=SOURCE.read_bytes();assert sha(raw)=='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142'
    text=raw.decode();tree=ast.parse(text);functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    device=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Device')
    methods={n.name:n for n in device.body if isinstance(n,ast.FunctionDef)}
    wanted_functions=['need','sha','read_owned'];wanted_methods=['identity','block_fact','current'];reuse={}
    constants=[]
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('VERSION','RELEASE','OLD_NOTES') for t in node.targets):
            constants.append(ast.get_source_segment(text,node))
    pieces=[]
    for name in wanted_functions:
        piece=ast.get_source_segment(text,functions[name]);pieces.append(piece);reuse[name]=sha(piece.encode())
    cls='class Probe:\n    def __init__(self):\n        self.carriers=None\n\n'
    for name in wanted_methods:
        piece=ast.get_source_segment(text,methods[name]);cls+='    '+piece+'\n\n';reuse['Probe.'+name]=sha(piece.encode())
    source='''"""Read-only actual #502 identity/full carriers/resident notes. Default is inert."""
from pathlib import Path
import hashlib,json,os,stat,struct,sys,time
'''+ '\n'.join(constants)+'\n\n'+'\n\n'.join(pieces)+'\n\n'+cls+'''
def main(request=None):
    if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
    if request is None:
        print(json.dumps(dict(source_only=True,device_accessed=False)));return 0
    need(request['schema']=='samurai-irq-rollback-current-probe-v1','bound current probe request')
    started=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    probe=Probe();before=probe.identity();current=probe.current(None);after=probe.identity()
    need(before==current['identity']==after,'identity changed during full current probe')
    print(json.dumps(dict(schema=request['schema'],request=request,identity_before=before,current=current,
        identity_after=after,started_boottime_ns=started,ended_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main(globals().get('PROBE_REQUEST')))
'''
    parsed=ast.parse(source)
    forbidden={'write','write_bytes','write_text','writelines','mkdir','unlink','Popen','system'}
    assert not any(isinstance(n,ast.Attribute) and n.attr in forbidden for n in ast.walk(parsed))
    assert not any(isinstance(n,ast.Attribute) and n.attr=='replace' and isinstance(n.value,ast.Name) and n.value.id=='os' for n in ast.walk(parsed))
    assert all(x not in source for x in ('O_RDWR','O_WRONLY','/dev/mem','REG14','exec('))
    with (HERE/'current-probe.py').open('x',encoding='utf-8',newline='\n') as file:file.write(source)
    with (HERE/'probe-reuse.json').open('x') as file:file.write(json.dumps(dict(source_sha256=sha(raw),
        probe_sha256=sha((HERE/'current-probe.py').read_bytes()),actual_unchanged_functions=reuse,
        device_accessed=False,runtime_identity_generated=False),indent=2)+'\n')
    print(json.dumps(dict(passed=True,actual_readonly_functions=len(reuse),runtime_request_generated=False)))


if __name__=='__main__':main()
