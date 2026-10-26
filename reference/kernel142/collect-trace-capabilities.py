"""Read-only tracer and CPU-idle metadata on the already validated boot."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

out = Path('/var/lib/samurai/k142-trace-capabilities')
boot = Path('/var/lib/samurai/k142-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
assert os.uname().version.startswith('#140 ') and not out.exists()
out.mkdir(mode=0o700)
out.joinpath('boot-id-private.txt').write_bytes(boot)
report = dict(stage=142, kernel_build=140, read_only=True, same_boot=True)
for name in ['available_tracers', 'current_tracer']:
    report[name] = Path('/sys/kernel/tracing').joinpath(name).read_text().strip()
report['functions'] = []
function_file = Path('/sys/kernel/tracing/available_filter_functions')
if function_file.exists():
    for line in function_file.read_text().splitlines():
        name = line.split()[0]
        if re.search(r'^(qcom_smp2p_intr|qcom_q6v5_.*|qcom_scm_.*|scm_.*|__scm_.*)$', name):
            report['functions'].append(name)
report['cpu_idle'] = {}
for cpu in Path('/sys/devices/system/cpu').glob('cpu[0-9]*'):
    states = {}
    for state in cpu.joinpath('cpuidle').glob('state*'):
        states[state.name] = {name: state.joinpath(name).read_text().strip()
            for name in ['name', 'desc', 'latency', 'residency', 'disable'] if state.joinpath(name).is_file()}
    report['cpu_idle'][cpu.name] = states
report['idle_driver'] = Path('/sys/devices/system/cpu/cpuidle/current_driver').read_text().strip()
report['irq17_affinity'] = Path('/proc/irq/17/smp_affinity_list').read_text().strip()
report['irq207_affinity'] = Path('/proc/irq/207/smp_affinity_list').read_text().strip()
report['kprobe_events_file_present'] = Path('/sys/kernel/tracing/kprobe_events').exists()
report['goal_complete'] = False
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
out.joinpath('capabilities-validation.json').write_text(json.dumps(report, indent=2)+'\n')
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n'
    for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k142-trace-capabilities-private.tar.gz', '.'], check=True, timeout=20)
print(json.dumps(report, indent=2))
