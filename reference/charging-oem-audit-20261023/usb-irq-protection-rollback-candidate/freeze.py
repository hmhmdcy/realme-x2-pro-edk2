"""Freeze software only: source-only contract, worker and narrow actual receipts."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    reuse=json.loads((HERE/'source-reuse.json').read_bytes());assert reuse['worker_sha256']==sha((HERE/'restore-worker.py').read_bytes())
    functions={n.name:ast.get_source_segment((HERE/'restore-worker.py').read_text(),n) for n in ast.parse((HERE/'restore-worker.py').read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    for name,item in reuse['helper_reuse'].items():assert sha(functions[name].encode())==item['sha256']
    for filename,count in [('test-result.json',21),('saved-proof-test-result.json',6)]:
        result=json.loads((HERE/filename).read_bytes());assert result['passed'] is True and result['count']==count
        for name,digest in result.get('tested_files',result.get('files',{})).items():assert sha((HERE/name).read_bytes())==digest
    local=[]
    for name in ('restore-worker.py','saved-proof.py'):
        child=subprocess.Popen([sys.executable,'-B',str(HERE/name)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=child.communicate();rc=child.wait();assert rc==0 and not stderr and json.loads(stdout)['source_only'] is True
        local.append(dict(source=name,pid=child.pid,terminal=True,returncode=rc,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
    with (HERE/'local-checks.json').open('x') as file:file.write(json.dumps(dict(passed=True,commands=local,device_accessed=False),indent=2)+'\n')
    contract=dict(schema='samurai-usb-irq-protection-rollback-contract-v1',source_only=True,
        worker_sha256=sha((HERE/'restore-worker.py').read_bytes()),payload_sha256='5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339',
        request_schema='samurai-usb-irq-protection-rollback-request-v1',transaction_regex='usb-irq-protection-rollback-[a-z0-9-]{8,48}',
        request_exact_fields=['schema','transaction_id','profile','identity','source_identity','source_stage','activation','payload_sha256','payload_base64','worker_sha256','lease_token'],
        profiles=['staged_same_boot_old_resident','booted_irq_new_resident','booted_original_new_resident'],
        current_identity_source='future actual original-key capture with exact Popen/input/terminal binding; never inferred from old adoption',
        source_stage_projection='unchanged stage-proof guard_stage_fields: seven fields/fourteen original remote facts',
        saved_source_API='review_profile_sources(profile,stage_directory,stage_fetch_directory,context_path=None)',
        connected_owner='reuse existing stage-host detached same-Popen/regular-request-stdin/finally-wait; not implemented here',
        worker_argv=['python3','-B','/root/charging-management-20261023/<transaction_id>/restore-worker.py','--execute-rollback'],
        worker_out='/root/charging-management-20261023/<transaction_id>/device-rollback',
        lease_path='/run/<transaction_id>-window-private.json',lease='exact original stage lease keys/current boot/token/camera+bluetooth released, <=120 BOOTTIME seconds',
        success_only='staged_original/runtime_pending',host_runtime_binding_or_supervisor_implemented=False,
        actual_request_or_guard_generated=False,device_accessed=False)
    with (HERE/'contract.json').open('x') as file:file.write(json.dumps(contract,indent=2)+'\n')
    names=[p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!='delivery.json']
    result=dict(schema='samurai-usb-irq-protection-rollback-offline-delivery-v1',passed=True,frozen=True,
        files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in sorted(names)},
        actual_affected_worker_cases=21,pure_saved_profile_wrapper_cases=6,unchanged_actual_helpers=10,
        old_suites_rerun=False,host_runtime_binding_or_supervisor_implemented=False,
        device_SSH_USB_PM_SDK_Git_build=False,actual_request_or_guard_generated=False,physical_acceptance=False)
    with (HERE/'delivery.json').open('x') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),worker_sha256=reuse['worker_sha256'])))


if __name__=='__main__':main()
