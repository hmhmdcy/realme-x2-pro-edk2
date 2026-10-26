"""Read/hash/extract frozen text only; no author imports, tests or builds."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF / 'charging-session-20261023/dwc-device-start-recovery-candidate'
PREVIOUS = REF / 'charging-oem-audit-20261023/dwc-device-sync-recovery-candidate'
BASE = REF / 'charging-oem-audit-20261023/apsd-integration/current-r7/snapshots'
PIN = '1f3aa44fa29c8f901c39a378ff4a7d546c447c40072e3e5283226857cfcb1349'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def extract(text, name):
    match = re.search(r'^(?:static )?(?:int|void|irqreturn_t|bool)\s+' + re.escape(name) + r'\([^;]*?\)\s*\{', text, re.M)
    assert match, name
    begin = text.index('{', match.start())
    depth = 0
    for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|' + r"'(?:\\.|[^'\\])*'|[{}]", text[begin:], re.S):
        if token.group() == '{':
            depth += 1
        elif token.group() == '}':
            depth -= 1
            if depth == 0:
                return text[match.start():begin + token.end()]
    raise AssertionError(name)


def main():
    assert sha(AUTHOR / 'delivery.json') == PIN
    delivery = json.loads((AUTHOR / 'delivery.json').read_bytes())
    assert delivery['passed'] and not delivery['deployed'] and not delivery['pm_unwind_complete']
    files = {}
    for name, expected in delivery['files'].items():
        assert sha(AUTHOR / name) == expected, name
        files[name] = dict(sha256=expected, bytes=(AUTHOR / name).stat().st_size)
    source = json.loads((AUTHOR / 'source-result.json').read_bytes())
    gadget = (AUTHOR / 'gadget.c').read_text()
    previous = (PREVIOUS / 'gadget.c').read_text()
    core = (BASE / 'drivers--usb--dwc3--core.c').read_text()
    for name, expected in source['previous'].items():
        assert sha(PREVIOUS / name) == expected
    for name, expected in source['original'].items():
        assert sha(BASE / ('drivers--usb--dwc3--' + name)) == expected
    assert (AUTHOR / 'core.h').read_bytes() == (PREVIOUS / 'core.h').read_bytes()
    name = 'dwc3_gadget_soft_connect'
    assert previous.replace(extract(previous, name), extract(gadget, name), 1) == gadget
    unchanged = source['previous_functions_unchanged']
    assert len(unchanged) == 16
    for name in unchanged:
        assert extract(previous, name) == extract(gadget, name), name
    manifest = json.loads((AUTHOR / 'function-manifest.json').read_bytes())
    fixture = (AUTHOR / 'tested-functions.inc').read_text()
    assert len(manifest) == 14
    for item in manifest:
        text = core if item['source'] == 'core.c(original)' else gadget
        body = extract(text, item['name'])
        assert hashlib.sha256(body.encode()).hexdigest() == item['sha256'], item['name']
        assert extract(fixture, item['name']) == body, item['name']
    receipt = json.loads((AUTHOR / 'test-result.json').read_bytes())
    assert receipt['passed'] and receipt['summary']['cases'] == 20 and receipt['summary']['groups'] == 6
    assert receipt['summary']['actual_functions'] == 14
    assert all(p['terminal'] and p['returncode'] == 0 for p in receipt['phases'])
    for name, expected in receipt['files'].items():
        assert sha(AUTHOR / name) == expected
    build = json.loads((AUTHOR / 'build-result.json').read_bytes())
    assert build['passed'] and build['phase']['terminal'] and build['phase']['returncode'] == 0
    assert build['phase']['pid'] == 786 and not build['diagnostic_lines']
    assert build['tracked_inputs_unchanged'] and build['parent_mounts_unchanged']
    assert build['inputs_before'] == build['inputs_after']
    for name, expected in build['files'].items():
        assert sha(AUTHOR / name) == expected
    caller = json.loads((AUTHOR / 'caller-evidence.json').read_bytes())
    reused = {}
    for relative, expected in caller['reused_evidence'].items():
        assert sha(REF / relative) == expected, relative
        reused[relative] = expected
    assert sha(AUTHOR / 'delivery.json') == PIN
    result = dict(
        schema='samurai-dwc-start-recovery-independent-review-v1',
        status='accepted_within_local_increment_scope', blocking_findings=[],
        author_delivery_sha256=PIN, files=files,
        whole_gadget_delta_only_soft_connect=True, previous_header_byte_equal=True,
        previous_functions_byte_equal=unchanged, actual_fixture_functions_matched=14,
        reused_evidence_bindings=reused,
        author_new_tests=dict(cases=20, groups=6, actual_functions=14, rerun_by_reviewer=False),
        author_object=dict(sha256=build['object_sha256'], bytes=build['object_size'],
                           terminal=build['phase']['terminal'], returncode=build['phase']['returncode'],
                           diagnostics=build['diagnostic_lines'], recompiled_by_reviewer=False),
        no_new_IRQ_or_event_buffer_allocation_release_in_increment=True,
        PM_common_ignored_gadget_errno_preserved=True,
        PM_unwind_complete=False, physical_HALT_verified=False,
        enumeration_or_real_suspend_recovery_verified=False,
        author_entrypoints_or_tests_run=False, build_or_storage_guard_used=False,
        device_or_transport_accessed=False, author_files_modified=False,
        review_sources={n: sha(HERE / n) for n in ('review.md', 'review-static.py')})
    target = HERE / 'review-result.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], result_sha256=sha(target))))


if __name__ == '__main__':
    main()
