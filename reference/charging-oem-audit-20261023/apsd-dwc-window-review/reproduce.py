"""One no-window exit regression using frozen actual r1 candidate functions."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'apsd-dwc-window-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
delivery = json.loads((CANDIDATE / 'delivery.json').read_bytes())
assert delivery['patch_sha256'] == 'e708a98cb38f0897328ee2a796f3145e3c022bb29037ce9e0ff5d402491fc287'
for name in ['core.h', 'core.c', 'gadget.c', 'test-window.c']:
    assert sha(CANDIDATE / name) == delivery['files'][name]
# Frozen test function extraction is copied as bytes into our own directory;
# no frozen generator/import/test is executed and no r1 byte is changed.
tests = json.loads((CANDIDATE / 'test-result.json').read_bytes())
for name in ['tested-functions.inc', 'tested-types.inc']:
    assert sha(CANDIDATE / name) == tests['fixtures'][name]
    (HERE / name).write_bytes((CANDIDATE / name).read_bytes())
fixture = (CANDIDATE / 'test-window.c').read_text()
old = '''static void usb_del_gadget(struct usb_gadget *g)
{assert(!mutex_destroyed);assert(dwc3_gadget_stop(g)==0);gadget_deletions++;}'''
new = '''static int teardown_pullup_ret;
static void usb_del_gadget(struct usb_gadget *g)
{
 assert(!mutex_destroyed);
 /* Actual source354 UDC core: gadget_unbind_driver first calls
  * usb_gadget_disconnect_locked -> ops->pullup(0), ignores its result,
  * then calls usb_gadget_udc_stop_locked -> ops->udc_stop. */
 teardown_pullup_ret=dwc3_gadget_pullup(g,0);
 assert(dwc3_gadget_stop(g)==0);
 gadget_deletions++;
}'''
assert fixture.count(old) == 1
fixture = fixture.replace(old, new).replace('int main(void)', 'int original_13_test_groups_not_run(void)')
fixture += '''
int main(void)
{
 struct dwc3 d;struct usb_gadget g={&d};setup(&d);d.gadget=&g;
 /* No begin, token, owner or extra PM reference. Running ordinary gadget. */
 assert(d.detect_window.state==DWC3_WINDOW_IDLE&&!d.detect_window.pm_ref);
 assert(d.pullups_connected&&!halted);
 dwc3_gadget_exit(&d);
 assert(teardown_pullup_ret==-ESHUTDOWN);
 assert(disconnects==0&&d.pullups_connected&&!halted);
 assert(free_irqs==1&&mutex_destroyed&&gadget_deletions==1&&!pm_refs);
 puts("{\\"reproduced\\":true,\\"active_window\\":false,\\"pullup_off_errno\\":-108,\\"soft_disconnect_calls\\":0,\\"halt_established\\":false,\\"irq_freed\\":true}");
 return 0;
}
'''
(HERE / 'test-no-window-exit.c').write_text(fixture)
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
build = subprocess.run(['gcc', *flags, str(HERE/'test-no-window-exit.c'), '-o', str(HERE/'test-no-window-exit')], capture_output=True, text=True)
assert build.returncode == 0, build.stderr
run = subprocess.run([str(HERE/'test-no-window-exit')], capture_output=True, text=True)
assert run.returncode == 0 and not run.stderr, (run.returncode,run.stdout,run.stderr)
result = dict(reviewed_patch_sha256=delivery['patch_sha256'], case=json.loads(run.stdout),
              actual_candidate_functions_unmodified=True, original_13_groups_rerun=False,
              source354_udc_call_order='usb_del_gadget -> gadget_unbind_driver -> usb_gadget_disconnect_locked -> pullup(0); then usb_gadget_udc_stop_locked -> udc_stop',
              fake_boundaries='PM/IRQ/MMIO/USB device core edges; actual frozen candidate exit/stop/pullup/window C functions',
              files={n:sha(HERE/n) for n in ['reproduce.py','test-no-window-exit.c','tested-functions.inc','tested-types.inc']},
              phone_accessed=False, ssh_executed=False, sdk_invoked=False, frozen_candidate_modified=False)
(HERE/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result['case'], indent=2))
