"""Collect the failed client's existing exit diagnostics, without a new capture."""
from pathlib import Path
import json,shlex,sys
import host
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1'
assert attempt.startswith('r') and attempt[1:].isdigit()
code=r'''from pathlib import Path
import json,shutil,subprocess
root=Path(ROOT)
logs=subprocess.check_output(['dmesg'],text=True)
text=(root/'1920x1080-isolated/client.log').read_text()
terms=['WARNING','ERROR','rejected','timeout','Timeout','Dropping','aborted','SIG','Segmentation','FATAL']
print(json.dumps(dict(core_pattern=Path('/proc/sys/kernel/core_pattern').read_text(),cores=[str(p) for p in root.rglob('core*')],tools={n:shutil.which(n) for n in ['gdb','gdbserver','eu-stack','coredumpctl']},diagnostics=[s for s in text.splitlines() if any(t in s for t in terms)],kernel_tail=logs[-3000:])))
'''.replace('ROOT',repr('/var/lib/samurai/k441-variable-pd10-'+attempt))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);q.check_returncode()
(host.PRIVATE/('exit-diagnostics-'+attempt+'-private.json')).write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps(dict(core_pattern=d['core_pattern'],cores=d['cores'],tools=d['tools'],diagnostics=d['diagnostics'][-25:],kernel_tail=d['kernel_tail'][-1000:]),indent=2))
