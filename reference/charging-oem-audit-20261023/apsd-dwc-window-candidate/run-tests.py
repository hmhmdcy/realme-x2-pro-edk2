"""Compile/execute actual window functions and check private patch boundaries."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prepare=subprocess.run(['python3',str(HERE/'prepare-tests.py')],capture_output=True,check=True)
spec=importlib.util.spec_from_file_location('window_actual',HERE/'make-candidate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=(HERE/'core.c').read_text();g=(HERE/'gadget.c').read_text()
for name in ['dwc3_suspend_common','dwc3_resume_common']:
 f=m.function(c,name)
 assert f.count('return ret;')==2 and f.count('return ')==2
 assert 'goto out;' in f and 'dwc3_gadget_window_pm_exit(dwc);' in f
exit_body=m.function(g,'dwc3_gadget_exit')
assert exit_body.index('dwc3_gadget_window_shutdown')<exit_body.index('cancel_work_sync')<exit_body.index('mutex_destroy')
assert exit_body.index('usb_del_gadget')<exit_body.index('cancel_work_sync')<exit_body.index('mutex_destroy')
assert m.function(g,'dwc3_gadget_stop').index('dwc3_gadget_window_shutdown')<m.function(g,'dwc3_gadget_stop').index('free_irq')
assert 'EXPORT_SYMBOL_GPL(dwc3_gadget_window' not in g
assert 'pm_runtime_resume_and_get(' not in (HERE/'window-functions.c.txt').read_text()
with tempfile.TemporaryDirectory() as t:
 root=Path(t);(root/'drivers/usb/dwc3').mkdir(parents=True)
 for n in ['core.h','core.c','gadget.c']:(root/'drivers/usb/dwc3'/n).write_bytes((HERE/'baseline'/n).read_bytes())
 patch=subprocess.run(['patch','--dry-run','-p1','-i',str(HERE/'dwc-window.patch')],cwd=root,capture_output=True)
 assert patch.returncode==0,patch.stderr.decode()
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer']
compiler=subprocess.run(['gcc',*flags,str(HERE/'test-window.c'),'-o',str(HERE/'test-window')],capture_output=True)
run=subprocess.run([str(HERE/'test-window')],capture_output=True) if compiler.returncode==0 else None
cases=[s[4:] for s in run.stdout.decode().splitlines() if s.startswith('ok: ')] if run else []
result=dict(passed=compiler.returncode==0 and run is not None and run.returncode==0 and len(cases)==13,
 actual_function_groups=cases,groups_count=len(cases),actual_functions=20,patch_dry_run=True,
 pm_error_exits_release_gate=True,shutdown_before_irq_free_and_mutex_destroy=True,mutex_destroy_after_usb_del_gadget=True,
 flags=flags,compile_returncode=compiler.returncode,compile_stderr=compiler.stderr.decode(),
 runtime_returncode=run.returncode if run else None,runtime_stdout=run.stdout.decode() if run else '',
 runtime_stderr=run.stderr.decode() if run else '',
 sources={n:sha(HERE/n) for n in ['core.h','core.c','gadget.c','dwc-window.patch']},
 fixtures={n:sha(HERE/n) for n in ['test-window.c','tested-types.inc','tested-functions.inc','tested-functions.json']},
 phone_accessed=False,ssh_executed=False,sdk_invoked=False,old_suites_repeated=False,
 scope='actual candidate C functions; fake PM/MMIO/lock boundaries and deterministic interleavings; not full lockdep or hardware validation')
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
