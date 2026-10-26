"""Read/AST/hash only. Never import author code or dispatch a process."""
from pathlib import Path
import ast
import hashlib
import json
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_bytes())


def check_files(folder, receipt):
    for name, entry in receipt['files'].items():
        digest = entry['sha256'] if isinstance(entry, dict) else entry
        assert sha(folder/name) == digest, name


def functions(p):
    text = p.read_text()
    return {node.name:ast.get_source_segment(text,node)
            for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}


def main():
    assert not sys.flags.optimize
    assert not (HERE/'review-result.json').exists(), 'Frozen review exists'
    assert sha(AUTHOR/'delivery.json') == '8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'
    delivery = read(AUTHOR/'delivery.json')
    assert delivery['revision'] == 2 and delivery['passed'] is True and delivery['frozen'] is True
    check_files(AUTHOR, delivery)
    assert sha(AUTHOR/'host.py') == '58d0cbf0dd4ec2db29725bdfd2b01467cbe04c4401b1ca411960438e66dca6e7'
    old = AUTHOR/'history/revision-1'
    assert sha(old/'delivery.json') == '18fc4976d54ec199a141162aecaa801e51ac78402741e27982997be9bf04eaa5'
    assert sha(old/'host.py') == '971e6e267700bd34193661c0ba1fbb525f1a55cab5e8ce20f063b21bb0694a5a'
    oldtext, newtext = (old/'host.py').read_text(), (AUTHOR/'host.py').read_text()
    delta = ("    need(child.get('stdin_sha256') == terminal.get('stdin_sha256') == sha(expected_payload),\n"
             "         'exact input payload must be bound to both original child receipts')\n")
    assert newtext.count(delta) == 1 and newtext.replace(delta,'') == oldtext
    oldfn, newfn = functions(old/'host.py'), functions(AUTHOR/'host.py')
    assert set(oldfn) == set(newfn)
    changed = [name for name in oldfn if oldfn[name] != newfn[name]]
    assert changed == ['saved_transport']
    prior = read(AUTHOR/'host-test-result.json')
    assert prior['passed'] is True and prior['count'] == 18 and prior['old_suites_rerun'] is False
    assert prior['files']['host.py'] == sha(old/'host.py')
    for name in ['identity-probe.py','test-host.py']:
        assert prior['files'][name] == sha(AUTHOR/name)
    r2 = read(AUTHOR/'input-binding-r2-result.json')
    assert r2['passed'] is True and r2['count'] == 5
    assert r2['actual_saved_transport_function'] is True
    assert r2['old_18_13_31_suites_rerun'] is False and r2['actual_payload_transmitted'] is False
    check_files(AUTHOR, r2)
    local = read(AUTHOR/'r2-local-check.json')
    assert local['passed'] is True and local['terminal'] is True and local['returncode'] == 0
    original_local = read(AUTHOR/'host-local-check.json')
    assert original_local['passed'] is True
    assert original_local['default_source_only']['terminal'] is True
    assert original_local['default_source_only']['returncode'] == 0
    assert original_local['final_source_missing_actual_material_refused_before_mkdir'] is True
    pins = read(AUTHOR/'host-source-pins.json')
    expected = {'stage_proof_frozen':'6f5a5b7e6ad2dcbb8a51115864571b44f1561eaddd4848a03f0687328fc4a3d3',
                'stage_proof':'85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093',
                'device_delivery':'b2c1d2de692b2d302450b0debbfdd50221b84790523829dc57b5c96ba271689b',
                'operator_delivery':'ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41',
                'completion_proof':'d4a7b29c3f5978c1254c4b7c40376fbf12453057d4ba8cc98cbb4ef7a952be00',
                'key_transport':'7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'}
    assert set(pins) == set(expected)
    for name, entry in pins.items():
        path = Path(entry['path'])
        assert sha(path) == entry['sha256'] == expected[name]
        if name in ['device_delivery','operator_delivery']:
            check_files(path.parent, read(path))
    stage = read(AUTHOR/'stage-proof-frozen.json')
    check_files(AUTHOR, stage)
    reuse = read(AUTHOR/'probe-source-reuse.json')
    device = REF/'charging-oem-audit-20261023/irq-cohort-postboot-readonly/device.py'
    assert sha(device) == reuse['source_sha256']
    assert sha(AUTHOR/'identity-probe.py') == reuse['probe_sha256']
    sourcefn, probefn = functions(device), functions(AUTHOR/'identity-probe.py')
    assert len(reuse['actual_functions']) == 6
    for name, digest in reuse['actual_functions'].items():
        assert sourcefn[name] == probefn[name]
        assert hashlib.sha256(probefn[name].encode()).hexdigest() == digest
    result = dict(schema=1,passed=True,reviewed_revision=2,new_blockers=[],
        author_delivery_sha256=sha(AUTHOR/'delivery.json'),host_sha256=sha(AUTHOR/'host.py'),
        previous_R1_not_accepted=True,R1_finding_sha256=sha(HERE/'r1-input-binding-finding.json'),
        R2_exact_delta='saved_transport requires both receipts stdin SHA256 to equal the exact expected payload',
        unchanged_host_functions=len(oldfn)-len(changed),exact_extracted_probe_functions=6,
        reused_R1_cases=18,new_R2_cases=5,stage_core_and_13_cases_unchanged=True,
        source_dependency_sha256=expected,
        accepted_boundaries=['actual completion and stage evidence re-review before payload/bind',
             'stage collection projection remains distinct from raw activation transaction and guard hash',
             'same twice-observed new boot differs from source boot; actual collection must retain that probed boot',
             'exact original-key endpoint/argv and same-child terminal/stdin/stdout/stderr receipts',
             'collector explicit execute/window/new-endpoint argv and frozen whole ten-check raw recomputation',
             'failure or malformed originals remain on disk; missing actual materials refuse before mkdir'],
        limitations=['host is an evidence reader/payload builder, not a transport dispatcher',
             'future sender must record exact input hash before sending and keep the same-child terminal proof',
             'author IO, stage/completion and original-key boundaries in cases are explicitly fake',
             'no actual runtime context, request, guard, new endpoint, boot, IRQ delivery or latency is accepted'],
        author_import_entry_or_tests_executed=False,
        device_USB_SSH_build_SDK_Git_used=False,
        own_files={name:sha(HERE/name) for name in ['review.py','README.md','r1-input-binding-finding.json',
                   'history/review-01-newline-normalization.json']})
    (HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,review_sha256=sha(HERE/'review-result.json'),
                          host_sha256=sha(AUTHOR/'host.py'))))


if __name__ == '__main__':
    main()
