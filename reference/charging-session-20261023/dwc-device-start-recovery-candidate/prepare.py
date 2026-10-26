"""Narrow start-error increment on the frozen synchronous DEVICE candidate.

Only local source/patch/fixture extraction; no build, device or old generator.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
PREV = REF / 'charging-oem-audit-20261023/dwc-device-sync-recovery-candidate'
BASE = PREV.parent / 'apsd-integration/current-r7/snapshots'
sha = lambda b: hashlib.sha256(b).hexdigest()


def extract(source, name):
    match = re.search(r'^(?:static )?(?:int|void|irqreturn_t|bool)\s+' + name +
                      r'\([^;]*?\)\s*\{', source, re.M)
    assert match, name
    start = match.start()
    pos = source.index('{', start)
    depth = 0
    for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'
                             r"'(?:\\.|[^'\\])*'|[{}]", source[pos:], re.S):
        if token.group() == '{':
            depth += 1
        if token.group() == '}':
            depth -= 1
            if not depth:
                return source[start:pos + token.end()]
    raise AssertionError(name)


def main():
    pins = {'gadget.c': '5d4ed305192653c0165a21b3037b7be2c80ff1491ad074b767a06363750c826a',
            'core.h': '9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'}
    for name, digest in pins.items():
        assert sha((PREV / name).read_bytes()) == digest, name
    previous = (PREV / 'gadget.c').read_text()
    original = (BASE / 'drivers--usb--dwc3--gadget.c').read_text()
    core = (BASE / 'drivers--usb--dwc3--core.c').read_text()
    assert sha((BASE / 'drivers--usb--dwc3--core.c').read_bytes()) == \
        'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf'
    old = extract(previous, 'dwc3_gadget_soft_connect')
    new = old.replace('\tint ret;', '\tunsigned long flags;\n\tint ret;', 1)
    assert new.count('\t__dwc3_gadget_start(dwc);') == 1
    new = new.replace('\t__dwc3_gadget_start(dwc);', '''\tret = __dwc3_gadget_start(dwc);
\tif (ret) {
\t\t/* No RUN_STOP was issued by this attempt. Clear device IRQs and
\t\t * both EP0 enables even when the partial start failed before the
\t\t * software pullup flag was set: soft_disconnect() would skip it.
\t\t * The event buffer/core stay valid for an already-running IRQ;
\t\t * this is not a proof of physical HALT or a core PM unwind.
\t\t */
\t\tspin_lock_irqsave(&dwc->lock, flags);
\t\t__dwc3_gadget_stop(dwc);
\t\tspin_unlock_irqrestore(&dwc->lock, flags);
\t\tdev_err(dwc->dev, "gadget endpoint start failed: %d; RUN_STOP skipped\\n",
\t\t\tret);
\t\treturn ret;
\t}''', 1)
    gadget = previous.replace(old, new, 1)
    assert gadget != previous
    # Every previous recovery/PM/lifecycle function remains verbatim.
    unchanged = ['__dwc3_gadget_start', '__dwc3_gadget_ep_disable', '__dwc3_gadget_stop',
                 'dwc3_gadget_disable_irq', 'dwc3_gadget_enable_irq',
                 'dwc3_gadget_recover_locked', 'dwc3_err_recovery_work',
                 'dwc3_schedule_err_recovery', 'dwc3_gadget_resume',
                 'dwc3_gadget_run_stop', 'dwc3_gadget_soft_disconnect',
                 'dwc3_gadget_suspend', 'dwc3_gadget_start', 'dwc3_gadget_stop',
                 'dwc3_gadget_pullup', 'dwc3_gadget_exit']
    for name in unchanged:
        assert extract(previous, name) == extract(gadget, name), name
    (HERE / 'gadget.c').write_text(gadget, newline='\n')
    (HERE / 'core.h').write_bytes((PREV / 'core.h').read_bytes())
    for name, before in [('start-cleanup.patch', previous), ('against-502.patch', original)]:
        patch = ''.join(difflib.unified_diff(before.splitlines(True), gadget.splitlines(True),
                        fromfile='a/drivers/usb/dwc3/gadget.c', tofile='b/drivers/usb/dwc3/gadget.c'))
        if name == 'against-502.patch':
            header = (BASE / 'drivers--usb--dwc3--core.h').read_text()
            patch += ''.join(difflib.unified_diff(header.splitlines(True),
                        (HERE / 'core.h').read_text().splitlines(True),
                        fromfile='a/drivers/usb/dwc3/core.h', tofile='b/drivers/usb/dwc3/core.h'))
        (HERE / name).write_text(patch, newline='\n')
    names = ['__dwc3_gadget_ep_disable', 'dwc3_gadget_disable_irq',
             '__dwc3_gadget_stop', '__dwc3_gadget_start', 'dwc3_gadget_soft_connect',
             'dwc3_gadget_run_stop', 'dwc3_gadget_soft_disconnect',
             'dwc3_gadget_recover_locked', 'dwc3_gadget_resume',
             'dwc3_core_soft_reset', 'dwc3_core_init_for_resume',
             'dwc3_resume_common', 'dwc3_runtime_resume', 'dwc3_pm_resume']
    core_names = set(names[-5:])
    # Prototypes permit the real production ordering without rewriting bodies.
    prototypes = '\n'.join(extract(core if n in core_names else gadget, n).split('{', 1)[0].strip() + ';'
                           for n in names)
    receipt = re.search(r'^struct dwc3_recovery_result \{.*?^\};', gadget, re.M | re.S).group()
    bodies = [extract(core if n in core_names else gadget, n) for n in names]
    (HERE / 'tested-functions.inc').write_text(receipt + '\n\n' + prototypes + '\n\n' +
                                              '\n\n'.join(bodies) + '\n', newline='\n')
    (HERE / 'previous-soft-connect.inc').write_text(extract(previous, 'dwc3_gadget_soft_connect').replace(
                        'dwc3_gadget_soft_connect(', 'previous_soft_connect(', 1) + '\n', newline='\n')
    manifest = [dict(name=n, source='core.c(original)' if n in core_names else 'gadget.c(candidate)',
                     sha256=sha(f.encode())) for n, f in zip(names, bodies)]
    (HERE / 'function-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    result = dict(previous=pins, original={n: sha((BASE / ('drivers--usb--dwc3--' + n)).read_bytes())
                    for n in ['core.c', 'core.h', 'gadget.c']},
                  candidate={n: sha((HERE / n).read_bytes()) for n in ['gadget.c', 'core.h']},
                  previous_functions_unchanged=unchanged,
                  changed_functions=['dwc3_gadget_soft_connect'],
                  core_c_unchanged=True, negative_gadget_error_not_propagated_to_core_pm=True,
                  no_halt_or_unwind_guarantee=True, source_commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8')
    (HERE / 'source-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(prepared=True, changed_functions=result['changed_functions'],
                         candidate=result['candidate'])))


if __name__ == '__main__':
    main()
