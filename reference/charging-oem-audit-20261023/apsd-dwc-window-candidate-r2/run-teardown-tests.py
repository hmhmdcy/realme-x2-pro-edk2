"""Only the affected teardown boundary; original 13 groups are compiled, not run."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'apsd-dwc-window-candidate'
REVIEW = HERE.parent / 'apsd-dwc-window-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old_delivery = json.loads((R1 / 'delivery.json').read_text())
assert old_delivery['patch_sha256'] == 'e708a98cb38f0897328ee2a796f3145e3c022bb29037ce9e0ff5d402491fc287'
for name, digest in old_delivery['files'].items():
    assert sha(R1 / name) == digest
assert json.loads((REVIEW / 'result.json').read_text())['case']['reproduced']
(HERE / 'r1-failure-review.json').write_bytes((REVIEW / 'result.json').read_bytes())
subprocess.run(['python3', str(HERE / 'prepare-tests.py')], check=True, capture_output=True)
before = {r['function']: r['sha256'] for r in json.loads((R1 / 'tested-functions.json').read_text())}
after = {r['function']: r['sha256'] for r in json.loads((HERE / 'tested-functions.json').read_text())}
assert before.keys() == after.keys()
changed_functions = [name for name in before if before[name] != after[name]]
assert changed_functions == ['dwc3_gadget_pullup']
for name in ['core.h', 'core.c', 'window-functions.c.txt']:
    assert sha(HERE / name) == sha(R1 / name)
diff = ''.join(difflib.unified_diff((R1 / 'gadget.c').read_text().splitlines(True),
    (HERE / 'gadget.c').read_text().splitlines(True), fromfile='r1/gadget.c', tofile='r2/gadget.c'))
(HERE / 'r1-to-r2.patch').write_text(diff)
fixture = (R1 / 'test-window.c').read_text()
old = '''static void usb_del_gadget(struct usb_gadget *g)
{assert(!mutex_destroyed);assert(dwc3_gadget_stop(g)==0);gadget_deletions++;}'''
new = '''static int teardown_pullup_ret;
static void usb_del_gadget(struct usb_gadget *g)
{
 assert(!mutex_destroyed);
 /* Source354 UDC: unbind first disconnects via pullup(0), ignores its
  * result, and later calls udc_stop. This OS boundary is not hardware. */
 teardown_pullup_ret=dwc3_gadget_pullup(g,0);
 assert(dwc3_gadget_stop(g)==0);
 gadget_deletions++;
}'''
assert fixture.count(old) == 1
fixture = fixture.replace(old, new).replace('int main(void)', 'int original_13_test_groups_not_run(void)')
old = 'static void free_irq(int irq,void *p){assert(!pm_refs&&current->detect_stopping);free_irqs++;}'
new = 'static void free_irq(int irq,void *p){assert(!pm_refs&&current->detect_stopping&&(halted||runtime_suspended));free_irqs++;}'
assert fixture.count(old) == 1
fixture = fixture.replace(old, new)
fixture += r'''
int main(void)
{
 struct dwc3 d;struct usb_gadget g={&d};struct dwc3_gadget_window_result r;
 setup(&d);d.gadget=&g;
 assert(d.detect_window.state==DWC3_WINDOW_IDLE&&!d.detect_window.pm_ref&&d.pullups_connected&&!halted);
 dwc3_gadget_exit(&d);
 assert(teardown_pullup_ret==0&&disconnects==1&&!d.pullups_connected&&halted&&free_irqs==1&&mutex_destroyed);
 done("no-window active exit disconnects before IRQ free");

 setup(&d);d.gadget=&g;runtime_suspended=true;halted=true;
 dwc3_gadget_exit(&d);
 assert(teardown_pullup_ret==0&&disconnects==0&&pm_sync_gets==0&&pm_barriers==1&&free_irqs==1&&mutex_destroyed);
 done("no-window suspended exit preserves original no-resume path");

 setup(&d);d.gadget=&g;r=begin(&d);assert(r.cookie);
 assert(dwc3_gadget_pullup(&g,0)==0&&disconnects==1&&pm_refs==1&&!pm_sync_gets&&!d.softconnect);
 dwc3_gadget_exit(&d);
 assert(teardown_pullup_ret==0&&disconnects==2&&!d.pullups_connected&&halted&&free_irqs==1&&mutex_destroyed&&pm_put_idle==1);
 done("owned window off remains intent-only then shutdown parks");

 setup(&d);d.gadget=&g;d.detect_stopping=true;
 assert(dwc3_gadget_pullup(&g,1)==-ESHUTDOWN&&!pm_sync_gets&&!disconnects);
 assert(dwc3_gadget_pullup(&g,0)==0&&disconnects==1&&halted&&!d.pullups_connected);
 dwc3_gadget_exit(&d);
 assert(teardown_pullup_ret==0&&free_irqs==1&&mutex_destroyed);
 done("stopping rejects reconnect but permits ordinary disconnect");

 setup(&d);d.gadget=&g;mutex_hook=shutdown_race;
 assert(dwc3_gadget_pullup(&g,0)==0&&disconnects==1&&halted&&!d.pullups_connected&&!pm_refs);
 assert(d.detect_stopping&&d.detect_window.state==DWC3_WINDOW_SHUTDOWN);
 dwc3_gadget_exit(&d);
 assert(teardown_pullup_ret==0&&free_irqs==1&&mutex_destroyed);
 done("shutdown after pullup PM acquisition cannot suppress off");
 return 0;
}
'''
(HERE / 'test-teardown.c').write_text(fixture)
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
compile_result = subprocess.run(['gcc', *flags, str(HERE / 'test-teardown.c'), '-o', str(HERE / 'test-teardown')], capture_output=True, text=True)
run = subprocess.run([str(HERE / 'test-teardown')], capture_output=True, text=True) if compile_result.returncode == 0 else None
cases = [line[4:] for line in run.stdout.splitlines() if line.startswith('ok: ')] if run else []
result = dict(passed=compile_result.returncode == 0 and run is not None and run.returncode == 0 and not run.stderr and len(cases) == 5,
    revision=2, actual_function_groups=cases, groups_count=len(cases),
    changed_actual_functions=changed_functions, unchanged_actual_functions=19,
    original_13_groups_rerun=False, original_delivery_sha256=sha(R1 / 'delivery.json'),
    original_patch_sha256=old_delivery['patch_sha256'],
    original_default_teardown_failure_confirmed=True, independent_review_sha256=sha(REVIEW / 'result.json'),
    original_13_receipt_sha256=sha(R1 / 'test-result.json'),
    compile_returncode=compile_result.returncode, compile_stderr=compile_result.stderr,
    runtime_returncode=run.returncode if run else None, runtime_stdout=run.stdout if run else '', runtime_stderr=run.stderr if run else '',
    flags=flags, sources={n:sha(HERE/n) for n in ['core.h','core.c','gadget.c','dwc-window.patch','r1-to-r2.patch']},
    fixtures={n:sha(HERE/n) for n in ['run-teardown-tests.py','test-teardown.c','tested-functions.inc','tested-types.inc','tested-functions.json']},
    scope='actual candidate C; source354 UDC unbind call order at fake OS/PM/MMIO/IRQ boundaries; no hardware or lockdep validation',
    phone_accessed=False, ssh_executed=False, sdk_invoked=False, frozen_r1_modified=False)
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
