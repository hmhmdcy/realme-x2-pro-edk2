"""Close the stopped version worker from retained facts; do not repeat capture/MMIO."""
from pathlib import Path
import ast
import json
import host

ROOT = Path(__file__).resolve().parent
template = ast.parse((ROOT.parent / 'kernel276/test-manager-lifetime.py').read_text())
node = next(n for n in template.body if isinstance(n, ast.Assign) and
            any(isinstance(x, ast.Name) and x.id == 'code' for x in n.targets) and isinstance(n.value, ast.Call))
code = ast.literal_eval(node.value.func.value)
# Reuse only imports and health functions, without creating a new work directory.
code = code[code.index('from pathlib import Path'):code.index('save();report={}')]
code = code.replace("os.umask(0o077);root=Path('/var/lib/samurai/k276-manager-lifetime-r1');root.mkdir(mode=0o700);state=dict(state='preflight',terminal=False,pid=os.getpid());proc=None;error=None",
                    "os.umask(0o077);root=Path('/var/lib/samurai/k280-version-r1')")
code += r'''
import re
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
state=json.loads((root/'state-private.json').read_text())
assert not Path('/proc',str(state['pid'])).exists()
child=Path('/proc',str(state['child_pid']))
if child.exists():
 fields=(child/'stat').read_text().rsplit(')',1)[1].split()
 assert fields[19]!=state['child_start_ticks'],'Original capture is still live'
log=(root/'wide-stdout-private.log').read_text()
sequence=[int(n) for n in re.findall(r'seq:\s*(\d+)',log)]
assert len(sequence)==120 and all(b>a for a,b in zip(sequence,sequence[1:]))
h=health();assert h['passed']
assert 'TypeError' in (root/'failure-private.txt').read_text()
report=dict(stage=280,versions=state['versions'],camera='wide',frames=len(sequence),
 original_worker_and_child_not_live=True,capture_exit_code_not_retained=True,
 initial_receipt_failed_due_to_health_helper_name_shadowing=True,
 no_capture_or_mmio_replayed=True,hardware_version_read_only=True,health=h)
(root/'recovered-summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
state.update(state='terminal-recovered-helper-failure',terminal=True,exit_code=1)
(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(report))
'''
run = host.ssh('python3 -', input=code.encode(), timeout=25)
data = json.loads(run.stdout)
(host.PRIVATE / 'version-recovered-private.json').write_bytes(run.stdout)
(ROOT / 'powered-version-validation.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({key: value for key,value in data.items() if key != 'health'}, indent=2))
print('Final health:', data['health']['passed'])
