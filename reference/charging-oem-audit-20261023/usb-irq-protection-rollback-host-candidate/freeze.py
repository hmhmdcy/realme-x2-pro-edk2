"""Freeze only the offline probe/request binder adapter and narrow receipts."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    result=json.loads((HERE/'test-result.json').read_bytes());assert result['passed'] is True and result['count']==12
    for name,digest in result['files'].items():assert sha((HERE/name).read_bytes())==digest
    reuse=json.loads((HERE/'probe-reuse.json').read_bytes());assert reuse['probe_sha256']==sha((HERE/'current-probe.py').read_bytes())
    text=(HERE/'current-probe.py').read_text();tree=ast.parse(text)
    actual={n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
    for cls in [n for n in tree.body if isinstance(n,ast.ClassDef)]:
        actual.update({cls.name+'.'+n.name:ast.get_source_segment(text,n) for n in cls.body if isinstance(n,ast.FunctionDef)})
    for name,digest in reuse['actual_unchanged_functions'].items():assert sha(actual[name].encode())==digest
    local=[]
    for name in ('bind.py','current-probe.py'):
        child=subprocess.Popen([sys.executable,'-B',str(HERE/name)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=child.communicate();rc=child.wait();assert rc==0 and not stderr and json.loads(stdout)['source_only'] is True
        local.append(dict(source=name,pid=child.pid,terminal=True,returncode=rc,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
    with (HERE/'local-checks.json').open('x') as file:file.write(json.dumps(dict(passed=True,commands=local,device_accessed=False),indent=2)+'\n')
    contract=dict(schema='samurai-usb-irq-protection-rollback-host-adapter-v1',source_only=True,
        API=['probe_payload(profile,stage_directory,stage_fetch_directory,context_path=None,*,endpoint=PEER)',
             'transport_argv(endpoint=PEER)','review_current(profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None)',
             'make_request(transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None)',
             'bind(out,transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None)'],
        current_identity_source='actual original-key double-bracket current probe only; never old adoption or pointer',
        current_probe_schema='samurai-irq-rollback-current-probe-v1',worker_request_schema='samurai-usb-irq-protection-rollback-request-v1',
        exact_reused_receipt_source='irq-cohort-postboot-host-candidate R2 saved_transport: both stdin hashes + original key/child/terminal/output',
        worker_sha256='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142',
        connected_launch_status_fetch_supervisor_implemented=False,existing_stage_owner_wiring_required=True,
        runtime_request_guard_lease_or_endpoint_capture_created=False,device_or_transport_accessed=False)
    with (HERE/'contract.json').open('x') as file:file.write(json.dumps(contract,indent=2)+'\n')
    names=[p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!='delivery.json']
    delivery=dict(schema='samurai-usb-irq-protection-rollback-host-delivery-v1',passed=True,frozen=True,
        files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in sorted(names)},
        new_adapter_cases=12,reused_actual_readonly_functions=6,old_21_6_20_suites_rerun=False,
        connected_owner_implemented=False,actual_runtime_request_or_guard_or_lease_generated=False,
        device_SSH_USB_PM_build_SDK_Git=False,physical_acceptance=False)
    with (HERE/'delivery.json').open('x') as file:file.write(json.dumps(delivery,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),binder_sha256=sha((HERE/'bind.py').read_bytes()))))


if __name__=='__main__':main()
