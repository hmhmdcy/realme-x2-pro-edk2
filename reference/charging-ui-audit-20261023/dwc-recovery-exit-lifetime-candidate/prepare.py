"""Derive only the recovery-work exit lifetime cut from frozen outcome inputs."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BASE = REF/'charging-session-20261023/dwc-device-resume-outcome-candidate'
PINS = {
    'gadget.c': '1080c78f3e29f1fd20ae5187e28ea114574e3131f24399647d2179e9be207859',
    'core.h': '6f6ec74e6634edb25beba1dcc09b924f5c004bb9234dbae16044986a0196cc05',
    'delivery.json': '293a2e962499e9e02a6062b2014fe23ea6e69932761cb2412c4c4b77dc0987d6',
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def function(text, name):
    match = re.search(r'^(?:static\s+)?(?:int|void|bool|irqreturn_t)\s+' + name +
                      r'\([^;]*?\)\s*\{', text, re.M)
    if match is None:
        raise ValueError(name)
    pos = text.index('{', match.start()) + 1
    end, depth = pos, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Nonunique source anchor: ' + before[:60])
    return text.replace(before, after, 1)


def main():
    if sys.flags.optimize:
        raise RuntimeError('Nonoptimized interpreter required')
    for name, digest in PINS.items():
        if sha((BASE/name).read_bytes()) != digest:
            raise ValueError(name)
    old_g, old_h = [(BASE/n).read_text() for n in ('gadget.c', 'core.h')]
    g = once(old_g,
        '\tdwc->err_state = DWC3_ERR_RECOVERY;\n\tschedule_work(&dwc->err_recovery_work);\n}',
        '\tdwc->err_state = DWC3_ERR_RECOVERY;\n'
        '\tif (!dwc->recovery_stopping)\n'
        '\t\tschedule_work(&dwc->err_recovery_work);\n}')
    g = once(g,
        '\tresult->reconnected = false;\n\t/* A synchronous resume failure',
        '\tresult->reconnected = false;\n'
        '\t/* Exit owns the closed recovery gate until the next gadget init.\n'
        '\t * A queued old worker must not touch a retiring controller.\n'
        '\t */\n'
        '\tif (dwc->recovery_stopping) {\n'
        '\t\tresult->stage = "gadget-exit";\n'
        '\t\tspin_unlock_irqrestore(&dwc->lock, flags);\n'
        '\t\treturn -ESHUTDOWN;\n'
        '\t}\n'
        '\t/* A synchronous resume failure')
    before = ('\tspin_unlock_irqrestore(&dwc->lock, flags);\n'
        '\t/* The IRQ already requested work; explicitly preserve an execution\n'
        '\t * opportunity even when its request coalesced with a running worker.\n'
        '\t * One call only: no synchronous second recovery or new retry loop.\n'
        '\t */\n'
        '\tif (result->pending)\n'
        '\t\tschedule_work(&dwc->err_recovery_work);\n\treturn ret;')
    after = ('\t/* Queue under the same lock as exit closes the producer gate.\n'
        '\t * Joining the running worker alone cannot prevent a later IRQ or\n'
        '\t * pending publication from rearming it. Keep the original pending\n'
        '\t * generation/state, but no execution after this gadget retires.\n'
        '\t */\n'
        '\tif (result->pending && !dwc->recovery_stopping)\n'
        '\t\tschedule_work(&dwc->err_recovery_work);\n'
        '\tspin_unlock_irqrestore(&dwc->lock, flags);\n\treturn ret;')
    g = once(g, before, after)
    g = once(g,
        '\tinit_completion(&dwc->ep0_in_setup);\n\tINIT_WORK(',
        '\tinit_completion(&dwc->ep0_in_setup);\n'
        '\t/* Previous gadget exit joined work and freed its IRQ before reuse.\n'
        '\t * No IRQ/UDC producer for this new gadget is registered yet.\n'
        '\t */\n'
        '\tdwc->recovery_stopping = false;\n\tINIT_WORK(')
    old_exit = function(g, 'dwc3_gadget_exit')
    new_exit = once(old_exit,
        '{\n\tif (!dwc->gadget)', '{\n\tunsigned long flags;\n\n\tif (!dwc->gadget)')
    new_exit = once(new_exit,
        '\tcancel_work_sync(&dwc->err_recovery_work);\n'
        '\tmutex_destroy(&dwc->connect_mutex);\n'
        '\tdwc3_enable_susphy(dwc, true);\n'
        '\tusb_del_gadget(dwc->gadget);',
        '\t/* Exclude both IRQ enqueue and recovery-publication requeue before\n'
        '\t * joining. Never join while holding connect_mutex: the worker\n'
        '\t * needs it. Leave it alive for usb_del_gadget() -> pullup/off ->\n'
        '\t * udc_stop/free_irq; no recovery producer can rearm in that gap.\n'
        '\t */\n'
        '\tspin_lock_irqsave(&dwc->lock, flags);\n'
        '\tdwc->recovery_stopping = true;\n'
        '\tspin_unlock_irqrestore(&dwc->lock, flags);\n'
        '\tcancel_work_sync(&dwc->err_recovery_work);\n'
        '\tdwc3_enable_susphy(dwc, true);\n'
        '\tusb_del_gadget(dwc->gadget);\n'
        '\tmutex_destroy(&dwc->connect_mutex);')
    g = once(g, old_exit, new_exit)
    h = once(old_h,
        ' * @err_event_seq: real IRQ error generations, serialized by lock\n',
        ' * @err_event_seq: real IRQ error generations, serialized by lock\n'
        ' * @recovery_stopping: exit-only recovery enqueue gate, protected by lock\n')
    h = once(h,
        '\tu64\t\t\terr_event_seq;\n',
        '\tu64\t\t\terr_event_seq;\n'
        '\t/* Only gadget init reopens this exit-owned producer gate. */\n'
        '\tbool\t\t\trecovery_stopping;\n')
    (HERE/'gadget.c').write_text(g, newline='\n')
    (HERE/'core.h').write_text(h, newline='\n')
    patch = ''.join(difflib.unified_diff(old_g.splitlines(True), g.splitlines(True),
        fromfile='a/drivers/usb/dwc3/gadget.c', tofile='b/drivers/usb/dwc3/gadget.c'))
    patch += ''.join(difflib.unified_diff(old_h.splitlines(True), h.splitlines(True),
        fromfile='a/drivers/usb/dwc3/core.h', tofile='b/drivers/usb/dwc3/core.h'))
    (HERE/'recovery-exit-lifetime.patch').write_text(patch, newline='\n')
    names = ['dwc3_schedule_err_recovery', 'dwc3_gadget_recover_locked',
             'dwc3_err_recovery_work', 'dwc3_gadget_pullup',
             'dwc3_gadget_stop', 'dwc3_gadget_exit']
    result_start = h.index('struct dwc3_recovery_result {')
    result_struct = h[result_start:h.index('};', result_start)+2]
    (HERE/'actual-functions.inc').write_text(result_struct+'\n\n'+
        '\n\n'.join(function(g, n) for n in names)+'\n', newline='\n')
    previous = []
    for n in ['dwc3_schedule_err_recovery', 'dwc3_gadget_recover_locked',
              'dwc3_err_recovery_work', 'dwc3_gadget_exit']:
        b = function(old_g, n)
        for other in names:
            if other not in ('dwc3_gadget_stop', 'dwc3_gadget_pullup'):
                b = b.replace(other+'(', 'previous_'+other+'(')
        previous.append(b)
    (HERE/'previous-functions.inc').write_text('\n\n'.join(previous)+'\n', newline='\n')
    changed = ['dwc3_schedule_err_recovery','dwc3_gadget_recover_locked',
               'dwc3_gadget_init','dwc3_gadget_exit']
    function_names = re.findall(r'^(?:static\s+)?(?:int|void|bool|irqreturn_t)\s+'
                                r'(dwc3_\w+|__dwc3_\w+)\([^;]*?\)\s*\{', old_g, re.M)
    unchanged = {}
    for n in function_names:
        if n not in changed:
            b = function(old_g, n)
            if b != function(g, n):
                raise ValueError('Unexpected function change: '+n)
            unchanged[n] = sha(b.encode())
    core = REF/'charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c'
    if sha(core.read_bytes()) != '5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f':
        raise ValueError('core source')
    result = dict(passed=True, source_inputs={str((BASE/n).relative_to(REF)).replace('\\','/'):v
        for n,v in PINS.items()}, core_unchanged_sha256=sha(core.read_bytes()),
        exact_changed_functions=changed, unchanged_functions=unchanged,
        new_field='bool recovery_stopping; /* dwc->lock; init/exit lifetime only */',
        candidate={n:sha((HERE/n).read_bytes()) for n in ['gadget.c','core.h',
                   'recovery-exit-lifetime.patch','actual-functions.inc','previous-functions.inc']},
        core_consumer_added=False, full_resume_abort_proved=False,
        init_gate_false_precedes_INIT_WORK_and_usb_add_gadget=True)
    (HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,changed_functions=changed,
                         gadget_sha256=sha(g.encode()),header_sha256=sha(h.encode()))))


if __name__ == '__main__':
    main()
