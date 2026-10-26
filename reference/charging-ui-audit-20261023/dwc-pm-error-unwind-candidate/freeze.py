"""Bind existing actual receipts; does not run tests, compiler or storage."""
from pathlib import Path
import difflib
import hashlib
import json
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if sys.flags.optimize:
        raise SystemExit('Nonoptimized interpreter required')
    assert not (HERE/'delivery.json').exists(), 'Frozen output exists'
    test = json.loads((HERE/'test-result.json').read_bytes())
    build = json.loads((HERE/'build-result.json').read_bytes())
    source = json.loads((HERE/'source-result.json').read_bytes())
    assert test['passed'] and test['summary']['cases'] == 24
    assert build['passed'] and build['phase']['terminal'] and build['phase']['returncode'] == 0
    assert not build['diagnostic_lines'] and build['tracked_inputs_unchanged']
    assert build['aarch64_relocatable'] and build['parent_mounts_unchanged_after_helper']
    assert not build['full_resume_error_unwind_complete']
    for receipt in [test, build]:
        for name, digest in receipt['files'].items():
            assert sha(HERE/name) == digest, name
    original = REF/'charging-oem-audit-20261023/usb-resume-errors/drivers--usb--dwc3--core.c'
    assert sha(original) == source['original_core_sha256']
    assert sha(HERE/'core.c') == source['candidate_core_sha256']
    patch = ''.join(difflib.unified_diff(original.read_text().splitlines(True),
                      (HERE/'core.c').read_text().splitlines(True),
                      fromfile='Image503/drivers/usb/dwc3/core.c',
                      tofile='candidate/drivers/usb/dwc3/core.c'))
    assert patch == (HERE/'suspend-susphy.patch').read_text()
    reused = [REF/'charging-session-20261023/dwc-device-start-recovery-candidate/test-result.json',
              REF/'charging-session-20261023/dwc-image503-start-recovery-candidate/delivery.json']
    files = {str(p.relative_to(HERE)).replace('\\','/'):
             dict(sha256=sha(p),bytes=p.stat().st_size)
             for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    delivery = dict(schema=1,passed=True,scope='failed-suspend SUSPHY bit restoration only',
                    files=files,historical_receipts={str(p.relative_to(REF)):sha(p) for p in reused},
                    new_actual_cases=24,old_20_126_rerun=False,
                    actual_object=dict(sha256=build['object_sha256'],bytes=build['object_size'],
                                       terminal=build['phase']),
                    full_resume_error_unwind_complete=False,softconnect_false_gap_unchanged=True,
                    Image_linked=False,deployed=False,device_or_SDK_used=False)
    (HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),
                          source_sha256=sha(HERE/'core.c'),test_sha256=sha(HERE/'test-result.json'),
                          build_sha256=sha(HERE/'build-result.json'))))


if __name__ == '__main__':
    main()
