"""Narrow once-owner specialization of frozen stage-host R2. No runtime material."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
STAGE=HERE.parent/'usb-irq-protection-stage-host-candidate-r2'
ACTIVATION=HERE.parent/'image502-logdump-activation-candidate/controller.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    need={'host.py':'84c53252d1993fc3ffce803e5c91d7cfe98f5a75c5f08e4e6c436d6615670660',
          'remote.py':'1dfeeb4fc8d6236750563c144e8d67603387c19b57bb1da5bbd1de594cfe8855',
          'supervisor.py':'b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'}
    old={name:(STAGE/name).read_bytes() for name in need}
    for name,raw in old.items():assert sha(raw)==need[name],name
    remote=old['remote.py'].decode()
    for before,after in [('usb-irq-protection-stage-','usb-irq-protection-rollback-'),('samurai-usb-irq-protection-stage-request-v1','samurai-usb-irq-protection-rollback-request-v1'),
        ('stage-worker.py','restore-worker.py'),('stage-supervisor.py','rollback-supervisor.py'),('device-stage','device-rollback'),('--execute-stage','--execute-rollback'),('STAGE_TRANSPORT','ROLLBACK_TRANSPORT')]:remote=remote.replace(before,after)
    start=remote.index("    guard = Path(request['adoption']['guard_path'])")
    end=remote.index('\n    identity_before = observed_identity()',start)
    remote=remote[:start]+'''    need(request['worker_sha256']=='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142','exact frozen rollback worker')

    def observed_identity():
        try:
            actual_boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        except (OSError,ValueError) as error:
            return dict(boot_id=None,source_boot_same=None,identity_matches=None,read_error=type(error).__name__)
        same=actual_boot==request['identity']['boot_id']
        result=dict(boot_id=actual_boot,source_boot_same=same,identity_matches=None)
        if same:
            try:
                actual=dict(boot_id=actual_boot,version=os.uname().version,
                    serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()),
                    compatible_sha256=sha(Path('/sys/firmware/devicetree/base/compatible').read_bytes()),
                    rootfs_sha256=sha(Path('/etc/samurai-rootfs-release').read_bytes()))
                result['identity_matches']=actual==request['identity']
            except (OSError,ValueError) as error:result['identity_error']=type(error).__name__
        return result
''' +remote[end:]
    remote=remote.replace("['guard_matches']","['identity_matches']").replace('boot/guard','boot/identity').replace('same original boot/guard','same original boot/identity')
    footer="    print(json.dumps(execute(ROLLBACK_TRANSPORT), indent=2), flush=True)"
    assert remote.count(footer)==1
    remote=remote.replace(footer,"    if 'ROLLBACK_TRANSPORT' in globals():\n        print(json.dumps(execute(ROLLBACK_TRANSPORT), indent=2), flush=True)\n    else:print(json.dumps(dict(source_only=True,device_accessed=False,worker_launched=False)))")
    supervisor=old['supervisor.py'].decode().replace('stage worker','rollback worker').replace('stage-worker.py','restore-worker.py').replace('stage-supervisor.py','rollback-supervisor.py').replace('--execute-stage','--execute-rollback')
    supervisor=supervisor.replace("    assert root.name == request['transaction_id'] == claim['transaction_id']", "    assert request['schema']=='samurai-usb-irq-protection-rollback-request-v1'\n    assert root.name == request['transaction_id'] == claim['transaction_id']")
    helpertext=old['host.py'].decode();helpernames={'local','need','create','save','load_module'}
    helpers=[];reuse={}
    for node in ast.parse(helpertext).body:
        if isinstance(node,ast.FunctionDef) and node.name in helpernames:
            segment=ast.get_source_segment(helpertext,node);helpers.append(segment);reuse[node.name]=dict(source='stage-host R2',sha256=sha(segment.encode()))
    activation=ACTIVATION.read_text()
    for node in ast.parse(activation).body:
        if isinstance(node,ast.FunctionDef) and node.name in {'process_identity','process_status'}:
            segment=ast.get_source_segment(activation,node);helpers.append(segment);reuse[node.name]=dict(source='Image502 activation controller',sha256=sha(segment.encode()))
    header='''"""Once rollback transport adapter. Default software checks never bind or connect."""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,json,os,re,secrets,subprocess,sys,time
if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
'''
    host=header+'\n\n'.join(helpers)+'\n\n'+(HERE/'host-body.py.inc').read_text()
    for name,text in [('host.py',host),('remote.py',remote),('supervisor.py',supervisor)]:
        ast.parse(text)
        with (HERE/name).open('w',encoding='utf-8',newline='\n') as file:file.write(text)
    report=dict(source_only=True,source_inputs={name:dict(path=str((STAGE/name).resolve()),sha256=sha(raw)) for name,raw in old.items()},
        activation_controller=dict(path=str(ACTIVATION.resolve()),sha256=sha(ACTIVATION.read_bytes())),
        unchanged_host_helpers=reuse,mechanically_specialized=['remote.py','supervisor.py'],
        actual_runtime_request_generated=False,device_or_transport_accessed=False)
    with (HERE/'source-reuse.json').open('w') as file:file.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,reused_host_helpers=len(reuse),runtime_request_generated=False)))


if __name__=='__main__':main()
