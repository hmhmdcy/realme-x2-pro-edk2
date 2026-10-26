"""Inspect standard trace facilities and capture tool availability, read-only."""
from pathlib import Path
import json
import host

ROOT = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
traces={}
for base in ['/sys/kernel/tracing','/sys/kernel/debug/tracing']:
 root=Path(base)
 if not (root/'available_filter_functions').exists():continue
 names=[l for l in (root/'available_filter_functions').read_text().splitlines() if any(n in l.split()[0] for n in ['vfe_hw_version','csid_hw_version'])]
 traces[base]=dict(functions=names,kprobe_events=(root/'kprobe_events').exists(),dynamic_events=(root/'dynamic_events').exists(),instances=(root/'instances').exists(),tracing_on=(root/'tracing_on').read_text().strip())
print(json.dumps(dict(trace=traces,devmem_exists=Path('/dev/mem').exists(),cam_tool=Path('/usr/bin/cam').exists())))
'''
run = host.ssh('python3 -', input=code.encode(), timeout=20)
data = json.loads(run.stdout)
(ROOT / 'trace-facilities-validation.json').write_text(json.dumps(dict(stage=280, **data), indent=2) + '\n')
print(json.dumps(data, indent=2))
