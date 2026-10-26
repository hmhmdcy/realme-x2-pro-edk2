"""Freeze offline host source/receipts only. No actual runtime identity is created."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    stage = json.loads((HERE/'stage-proof-frozen.json').read_bytes())
    assert stage['passed'] is True and stage['stage_proof_sha256']=='85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093'
    for name,item in stage['files'].items():assert sha((HERE/name).read_bytes())==item['sha256']
    test = json.loads((HERE/'host-test-result.json').read_bytes())
    assert test['passed'] is True and test['count']==18
    for name,digest in test['files'].items():assert sha((HERE/name).read_bytes())==digest
    for name in ('host.py','identity-probe.py'):ast.parse((HERE/name).read_bytes())
    child=subprocess.Popen([sys.executable,'-B',str(HERE/'host.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();rc=child.wait()
    assert rc==0 and not stderr and json.loads(stdout)==dict(source_only=True,
        source_stage_or_activation_reviewed=False,runtime_request_generated=False,device_or_transport_accessed=False)
    spec=importlib.util.spec_from_file_location('final_irq_postboot_source',HERE/'host.py')
    host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    with tempfile.TemporaryDirectory(prefix='irq-host-final-source-') as temp:
        out=Path(temp)/'must-not-exist'
        try:host.bind(out,Path(temp)/'missing-context',Path(temp)/'missing-camera',Path(temp)/'missing-probe')
        except (ValueError,FileNotFoundError):pass
        else:raise AssertionError('missing actual activation was accepted')
        assert not out.exists()
    local=dict(passed=True,default_source_only=dict(pid=child.pid,terminal=True,returncode=rc,
        stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)),
        final_source_missing_actual_material_refused_before_mkdir=True,
        actual_runtime_request_generated=False,device_or_transport_accessed=False)
    with (HERE/'host-local-check.json').open('x') as file:file.write(json.dumps(local,indent=2)+'\n')
    names=[p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!='delivery.json']
    delivery=dict(schema='samurai-irq-cohort-postboot-host-delivery-v1',passed=True,frozen=True,
        files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in sorted(names)},
        pure_stage_boundary_cases=13,new_host_boundary_cases=18,
        old_suites_rerun=False,actual_stage_activation_postboot_request_or_guard_generated=False,
        device_SSH_USB_build_SDK_Git=False,physical_delivery_or_latency_accepted=False)
    with (HERE/'delivery.json').open('x') as file:file.write(json.dumps(delivery,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),
        host_sha256=sha((HERE/'host.py').read_bytes()),pure_stage_proof_unchanged=True)))


if __name__=='__main__':main()
