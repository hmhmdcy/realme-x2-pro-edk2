"""Freeze only authorized R2 stdin evidence gate and retained R1 source history."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    history=HERE/'history/revision-1'
    prior=(history/'delivery.json').read_bytes()
    assert sha(prior)=='18fc4976d54ec199a141162aecaa801e51ac78402741e27982997be9bf04eaa5'
    old=json.loads(prior)
    for name,item in old['files'].items():
        path=history/'host.py' if name=='host.py' else history/'README-original.md.inc' if name=='README.md' else HERE/name
        assert sha(path.read_bytes())==item['sha256'], 'R1 original changed: '+name
    test=json.loads((HERE/'input-binding-r2-result.json').read_bytes())
    assert test['passed'] is True and test['count']==5
    for name,digest in test['files'].items():assert sha((HERE/name).read_bytes())==digest
    a=(history/'host.py').read_text();b=(HERE/'host.py').read_text()
    added="    need(child.get('stdin_sha256') == terminal.get('stdin_sha256') == sha(expected_payload),\n         'exact input payload must be bound to both original child receipts')\n"
    assert b.replace(added,'',1)==a and b.count(added)==1
    patch=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='R1/host.py',tofile='R2/host.py'))
    with (HERE/'revision-1-to-2.patch').open('x') as file:file.write(patch)
    child=subprocess.Popen([sys.executable,'-B',str(HERE/'host.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();rc=child.wait()
    assert rc==0 and not stderr and json.loads(stdout)['source_only'] is True
    local=dict(passed=True,pid=child.pid,terminal=True,returncode=rc,
        stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),device_or_transport_accessed=False)
    with (HERE/'r2-local-check.json').open('x') as file:file.write(json.dumps(local,indent=2)+'\n')
    names=[p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p!=HERE/'delivery.json']
    result=dict(schema='samurai-irq-cohort-postboot-host-delivery-v1',revision=2,passed=True,frozen=True,
        previous_delivery_sha256=sha(prior),
        files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in sorted(names)},
        pure_stage_proof_unchanged=True,pure_stage_proof_sha256='85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093',
        only_source_delta='both original child receipts require exact stdin SHA256',
        new_input_binding_cases=5,reused_R1_host_cases=18,reused_pure_stage_cases=13,
        old_18_13_31_suites_rerun=False,actual_stage_activation_postboot_request_or_guard_generated=False,
        actual_payload_transmitted=False,device_SSH_USB_build_SDK_Git=False,physical_delivery_or_latency_accepted=False)
    (HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),host_sha256=sha((HERE/'host.py').read_bytes()))))


if __name__=='__main__':main()
