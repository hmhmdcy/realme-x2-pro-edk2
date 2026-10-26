"""Adapt the frozen eight-object method to original #502 and this exact leaf."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[2]
ORIGINAL=REF/'charging-session-20261023/dwc-device-resume-outcome-candidate/object-build/build-eight.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
raw=ORIGINAL.read_bytes()
assert sha(raw)=='6c78666b4e18444522de90d56dbc5b8eb55e57731a2cc00b967472b6c9a658f0'
text=raw.decode()
text=text.replace('Eight explicit private compiler invocations from #503 commands, no make/link.',
    'Eight explicit private compiler invocations from actual #502 commands, no make/link.')
text=text.replace('dwc-image503-start-recovery-01','gauge-image502-notify-01')
text=text.replace('dwc-device-resume-outcome-objects-01','dwc-vbus-budget-fence-objects-01')
text=text.replace('storage284_dwc_outcome_objects','storage284_dwc_budget_objects')
text=text.replace("    if sys.flags.optimize or os.geteuid() != 0:",
    "    assert sys.argv[1:] == ['--execute'], 'Explicit --execute required'\n    if sys.flags.optimize or os.geteuid() != 0:")
text=text.replace('293a2e962499e9e02a6062b2014fe23ea6e69932761cb2412c4c4b77dc0987d6',
    '8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa')
start=text.index("    for name, digest in source['source_inputs'].items():")
end=text.index("    helper = REF/'kernel284/storage.py'",start)
text=text[:start]+'''    for name, digest in source['candidate'].items():
        assert sha(LEAF/name) == digest, name
    public502 = REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
    original_result_path = public502/'build-result.json'
    assert sha(original_result_path) == 'feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6'
    original_result = json.loads(original_result_path.read_bytes())
    assert original_result['passed'] and original_result['child_returncode'] == 0
    assert sha(BASE/'result.json') == sha(original_result_path)
'''+text[end:]
text=text.replace("'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314'",
    "'9eec86e42945a786447e6a6548a25b495e29a01bed8e8fbfc13e02903e1ff0c5'")
text=text.replace("'9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'",
    "'525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c'")
start=text.index("    for name in [*TARGETS,'vmlinux','arch/arm64/boot/Image']:")
end=text.index('    cmdpaths = ',start)
text=text[:start]+'''    for name in ['vmlinux','arch/arm64/boot/Image']:
        assert sha(BASE/'build'/name) == original_result['build']['outputs'][name]['sha256'], name
    scope_path = REF/'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json'
    assert sha(scope_path) == 'bec66bdf580ce4541f19b60fb5f4865649f48376ba5bbfcc159424455fef8b46'
    scope = json.loads(scope_path.read_bytes())
    assert scope['passed'] and set(scope['required_object_targets']) == set(TARGETS)
    rows = {row['target']:row for row in scope['core_h_dependencies']}
    for target in TARGETS:
        row = rows[target]
        assert sha(BASE/'build'/target) == row['object_sha256'], target
        assert sha(BASE/'build'/row['cmd_path']) == row['cmd_sha256'], target
        assert sha(BASE/'source354'/row['source_path']) == row['source_sha256'], target
'''+text[end:]
text=text.replace("helper, public503/'build-result.json', public503/'delivery.json', scope_path,",
    "helper, original_result_path, scope_path, LEAF/'delivery.json', LEAF/'test-result.json',\n        *[LEAF/name for name in ['core.c','core.h','gadget.c']],")
text=text.replace("['.config','Module.symvers','vmlinux','arch/arm64/boot/Image',*TARGETS]",
    "['.config','Module.symvers','vmlinux.symvers','include/generated/autoconf.h','vmlinux','arch/arm64/boot/Image',*TARGETS]",1)
text=text.replace("'core.c':REF/'charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c'",
    "'core.c':LEAF/'core.c'")
text=text.replace("original_source503=originals", "original_source502=originals")
text=text.replace("tracked_source503_shared_inputs_unchanged", "tracked_source502_shared_inputs_unchanged")
text=text.replace("source_503_delivery_sha256=sha(public503/'delivery.json')",
    "source_502_build_receipt_sha256=sha(original_result_path)")
text=text.replace('PM_unwind_complete=False,device_SSH_USB_SDK_Git_used=False',
    'software_budget_only=True,PM_unwind_complete=False,device_SSH_USB_SDK_Git_used=False')
assert 'public503' not in text and 'dwc-pm-error-unwind-candidate' not in text
assert text.count("'core.c':LEAF/'core.c'")==1
(HERE/'build-eight.py').write_text(text,encoding='utf-8',newline='\n')
result=dict(passed=True,original_builder_path=str(ORIGINAL),original_builder_sha256=sha(raw),
    new_builder_sha256=sha((HERE/'build-eight.py').read_bytes()),
    original502_base=True,no_503_or_outcome_source_selected=True,source_delivery_sha256='8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa',
    changes='actual502 base/receipts/all eight original command+object+source hashes; three exact local sources; unique output; original guard and eight direct compiler/wait algorithm retained',executed=False)
(HERE/'derivation-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
