"""Pinned stack-only DEVICE outcome candidate. Never edits its inputs."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
INPUTS = {
    'gadget.c': ('charging-ui-audit-20261023/dwc-suspend-retry-candidate/gadget.c',
                 '1f47ecbd54f931ccd1068b23c4e171864966f652cdf85986f89e151f386cf354'),
    'core.h': ('charging-session-20261023/dwc-device-start-recovery-candidate/core.h',
               '9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'),
    'core.c': ('charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c',
               '5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f'),
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def function(text, name):
    match = re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|void|bool)\s+' + name +
                      r'\([^;]*?\)\s*\{', text, re.M)
    assert match, name
    end = text.index('{', match.start()) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


DEVICE = '''static void dwc3_gadget_resume_device(struct dwc3 *dwc,
\t\t\t\t      struct dwc3_device_resume_result *result)
{
\tunsigned long flags;

\t*result = (struct dwc3_device_resume_result) {
\t\t.requested = true,
\t\t.detail.stage = "initial-connect",
\t};
\tmutex_lock(&dwc->connect_mutex);
\tspin_lock_irqsave(&dwc->lock, flags);
\tresult->detail.start_seq = dwc->err_event_seq;
\tresult->detail.end_seq = result->detail.start_seq;
\tspin_unlock_irqrestore(&dwc->lock, flags);
\t/* Preserve the original first attempt, even with an old error state.
\t * Only the synchronous recovery claim refuses to revive it.
\t */
\tresult->primary = dwc3_gadget_soft_connect(dwc);
\tif (result->primary) {
\t\tresult->recovery_attempted = true;
\t\tresult->recovery = dwc3_gadget_recover_locked(dwc, true,
\t\t\t\t\t\t\t &result->detail);
\t\tresult->operation_completed = result->detail.reconnected &&
\t\t\t!result->detail.pending &&
\t\t\t!pm_runtime_suspended(dwc->dev);
\t\tdev_err(dwc->dev,
\t\t\t"DEVICE resume primary=%d recovery=%d stage=%s seq=%llu->%llu pending_at_publish=%u\\n",
\t\t\tresult->primary, result->recovery, result->detail.stage,
\t\t\t(unsigned long long)result->detail.start_seq,
\t\t\t(unsigned long long)result->detail.end_seq,
\t\t\tresult->detail.pending);
\t} else {
\t\tspin_lock_irqsave(&dwc->lock, flags);
\t\tresult->detail.end_seq = dwc->err_event_seq;
\t\tresult->detail.pending = result->detail.end_seq !=
\t\t\tresult->detail.start_seq;
\t\tresult->detail.reconnected = true;
\t\tresult->detail.stage = "initial-connect-complete";
\t\t/* A zero primary does not clear an older failure or queued
\t\t * recovery. This is a publication snapshot, not exclusion of
\t\t * future IRQ/work or permission for core/PHY teardown.
\t\t */
\t\tresult->operation_completed = !result->detail.pending &&
\t\t\tdwc->err_state == DWC3_ERR_NONE &&
\t\t\t!pm_runtime_suspended(dwc->dev);
\t\tspin_unlock_irqrestore(&dwc->lock, flags);
\t}
\tmutex_unlock(&dwc->connect_mutex);
}

/* Internal same-Image DEVICE interface. The caller must retain the bound
 * controller and powered core/PHY for the complete synchronous operation.
 * No result here supplies failed-attempt abort or PM-unwind ownership.
 */
void dwc3_gadget_resume_result(struct dwc3 *dwc,
\t\t\t       struct dwc3_device_resume_result *result)
{
\t*result = (struct dwc3_device_resume_result) {
\t\t.detail.stage = "not-requested",
\t};
\tif (!dwc->gadget_driver || !dwc->softconnect)
\t\treturn;
\tif (dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE) {
\t\tresult->primary = -EOPNOTSUPP;
\t\tresult->detail.stage = "not-device";
\t\treturn;
\t}
\tdwc3_gadget_resume_device(dwc, result);
}

int dwc3_gadget_resume(struct dwc3 *dwc)
{
\tstruct dwc3_device_resume_result result;

\tif (!dwc->gadget_driver || !dwc->softconnect)
\t\treturn 0;
\t/* HOST is not a gadget caller; keep OTG's original connect behavior. */
\tif (dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE)
\t\treturn dwc3_gadget_soft_connect(dwc);

\tdwc3_gadget_resume_device(dwc, &result);
\t/* Preserve the legacy primary errno, including after a successful
\t * reconnect. Core PM does not consume the new outcome in this leaf.
\t */
\treturn result.primary;
}'''

STRUCTS = '''/* Stack-only attempt receipts, not controller terminal state, HALT proof,
 * IRQ-depth ownership or permission to release core/PHY resources.
 */
struct dwc3_recovery_result {
\tconst char *stage;
\tu64 start_seq, end_seq;
\tbool pending;
\t/* Only an actual soft_connect() return of zero sets this fact. */
\tbool reconnected;
};

struct dwc3_device_resume_result {
\tint primary;
\tint recovery;
\tbool requested;
\tbool recovery_attempted;
\t/* Completed at publication; a later IRQ/worker is still possible. */
\tbool operation_completed;
\tstruct dwc3_recovery_result detail;
};

'''


def main():
    if sys.flags.optimize:
        raise RuntimeError('nonoptimized source preparation required')
    original = {}
    for name, (path, digest) in INPUTS.items():
        raw = (REF / path).read_bytes()
        assert sha(raw) == digest, path
        original[name] = raw.decode().replace('\r\n', '\n')
    gadget, header = original['gadget.c'], original['core.h']
    old_struct = '''/* Stack-only receipt, not a controller terminal state or IRQ-depth owner. */
struct dwc3_recovery_result {
\tconst char *stage;
\tu64 start_seq, end_seq;
\tbool pending;
};

'''
    assert gadget.count(old_struct) == 1
    gadget = gadget.replace(old_struct, '')
    old_helper = function(gadget, 'dwc3_gadget_recover_locked')
    new_helper = old_helper.replace('result->pending = false;',
                                    'result->pending = false;\n\tresult->reconnected = false;', 1)
    old_complete = '\t\tif (!ret)\n\t\t\tresult->stage = "connect-complete";'
    new_complete = '\t\tif (!ret) {\n\t\t\tresult->reconnected = true;\n\t\t\tresult->stage = "connect-complete";\n\t\t}'
    assert new_helper.count(old_complete) == 1
    new_helper = new_helper.replace(old_complete, new_complete)
    gadget = gadget.replace(old_helper, new_helper)
    old_resume = function(gadget, 'dwc3_gadget_resume')
    gadget = gadget.replace(old_resume, DEVICE)
    marker = '/* power management interface */\n'
    assert header.count(marker) == 1
    header = header.replace(marker, STRUCTS + marker)
    decl = 'int dwc3_gadget_resume(struct dwc3 *dwc);'
    assert header.count(decl) == 1
    header = header.replace(decl, decl + '\nvoid dwc3_gadget_resume_result(struct dwc3 *dwc,\n'
                            '\t\t\t       struct dwc3_device_resume_result *result);')
    host_int = function(header, 'dwc3_gadget_resume')
    host_result = '''static inline void dwc3_gadget_resume_result(struct dwc3 *dwc,
\t\t\t       struct dwc3_device_resume_result *result)
{
\t*result = (struct dwc3_device_resume_result) {
\t\t.detail.stage = "host-only",
\t};
}'''
    header = header.replace(host_int, host_int + '\n\n' + host_result)
    patch = []
    for name, text in [('gadget.c', gadget), ('core.h', header)]:
        (HERE / name).write_text(text, newline='\n')
        patch.extend(difflib.unified_diff(original[name].splitlines(True), text.splitlines(True),
                     fromfile='a/drivers/usb/dwc3/' + name, tofile='b/drivers/usb/dwc3/' + name))
    (HERE / 'device-resume-outcome.patch').write_text(''.join(patch), newline='\n')
    names = ['dwc3_gadget_run_stop', 'dwc3_gadget_disable_irq', '__dwc3_gadget_stop',
             'dwc3_gadget_soft_disconnect', 'dwc3_gadget_soft_connect', 'dwc3_schedule_err_recovery',
             'dwc3_gadget_recover_locked', 'dwc3_gadget_resume_device',
             'dwc3_gadget_resume_result', 'dwc3_gadget_resume']
    bodies = {name: function(gadget, name) for name in names}
    (HERE / 'actual-functions.inc').write_text(STRUCTS + '\n\n'.join(bodies.values()) + '\n', newline='\n')
    (HERE / 'host-stubs.inc').write_text(STRUCTS + host_int + '\n\n' + host_result + '\n', newline='\n')
    (HERE / 'previous-resume.inc').write_text(old_resume.replace('dwc3_gadget_resume(',
             'previous_gadget_resume(', 1) + '\n', newline='\n')
    changed = {'dwc3_gadget_recover_locked', 'dwc3_gadget_resume_device',
               'dwc3_gadget_resume_result', 'dwc3_gadget_resume'}
    reused = {}
    for name, body in bodies.items():
        if name not in changed:
            assert body == function(original['gadget.c'], name), name
            reused[name] = sha(body.encode())
    # The entire persistent controller declaration and export statements remain exact.
    old_dwc = re.search(r'^struct dwc3 \{.*?^};', original['core.h'], re.S | re.M).group()
    new_dwc = re.search(r'^struct dwc3 \{.*?^};', header, re.S | re.M).group()
    assert old_dwc == new_dwc
    exports = lambda text: re.findall(r'^EXPORT_SYMBOL.*$', text, re.M)
    assert exports(gadget) == exports(original['gadget.c'])
    result = dict(passed=True, source_inputs={p: h for p, h in INPUTS.values()},
        core_source_unchanged_not_copied=True, persistent_dwc_declaration_sha256=sha(old_dwc.encode()),
        existing_exports_unchanged=True, old_wrapper_skip_and_OTG_prefix_unchanged=
            old_resume[old_resume.index('\tif (!dwc->gadget_driver'):old_resume.index('\n\tmutex_lock')] ==
            function(gadget, 'dwc3_gadget_resume')[function(gadget, 'dwc3_gadget_resume').index('\tif (!dwc->gadget_driver'):
            function(gadget, 'dwc3_gadget_resume').index('\n\tdwc3_gadget_resume_device')],
        exact_reused_functions=reused, extracted_actual_functions=len(bodies),
        candidate_sha256={n: sha((HERE/n).read_bytes()) for n in ['gadget.c', 'core.h',
            'device-resume-outcome.patch', 'actual-functions.inc', 'host-stubs.inc', 'previous-resume.inc']},
        core_consumer_added=False, PM_unwind_proved=False, new_persistent_fields=False)
    assert result['old_wrapper_skip_and_OTG_prefix_unchanged']
    (HERE/'source-result.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(json.dumps(dict(passed=True, actual_functions=len(bodies), **result['candidate_sha256'])))


if __name__ == '__main__':
    main()
