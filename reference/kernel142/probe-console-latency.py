"""One reversible console-routing A/B with the screen already idle/off.

Both informational records stay in dmesg. Only the second record bypasses
console transmission. Restore ignore_loglevel and CPU affinity in finally.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

out = Path('/var/lib/samurai/k142-console-latency-ab')
trace = Path('/sys/kernel/tracing/instances/k142-console-ab')
parameter = Path('/sys/module/printk/parameters/ignore_loglevel')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = Path('/var/lib/samurai/k142-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid() == 0 and boot_path.read_bytes() == boot
assert os.uname().version.startswith('#140 ') and not out.exists() and not trace.exists()
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text(), 'Wait for the already idle/off display'
original_ignore = parameter.read_text().strip()
original_printk = Path('/proc/sys/kernel/printk').read_text()
original_affinity = os.sched_getaffinity(0)
assert original_ignore == 'Y' and int(original_printk.split()[0]) == 1
assert 0 in original_affinity and int(Path('/proc/sys/kernel/tainted').read_text()) == 0
out.mkdir(mode=0o700)
out.joinpath('boot-id-private.txt').write_bytes(boot)

def dmesg():
    return subprocess.run(['dmesg'], capture_output=True, text=True, check=True).stdout

def counts(text):
    return {key: text.count(value) for key, value in [('dpu', 'frame done timeout'),
        ('dsi', 'dsi_err_worker'), ('gpu', 'gpu fault:'), ('warn', 'WARNING:'), ('tx_dma', 'unable to prepare channel')]}

before = dmesg()
out.joinpath('dmesg-before-private.txt').write_text(before)
samples = []
error = None
trace.mkdir()
try:
    trace.joinpath('tracing_on').write_text('0')
    trace.joinpath('buffer_size_kb').write_text('4096')
    trace.joinpath('trace_clock').write_text('mono')
    for event in ['irq_handler_entry', 'irq_handler_exit', 'cpu_idle', 'sched_switch']:
        paths = list(trace.joinpath('events').glob('*/'+event+'/enable'))
        assert len(paths) == 1
        paths[0].write_text('1')
    trace.joinpath('tracing_on').write_text('1')
    os.sched_setaffinity(0,{0})
    for label, ignore in [('A','Y'),('B','N')]:
        assert boot_path.read_bytes() == boot
        parameter.write_text(ignore+'\n')
        assert parameter.read_text().strip() == ignore
        payload = '<6>K142 console latency '+label+' '+('x'*50)+'\n'
        trace.joinpath('trace_marker').write_text('K142_CONSOLE_'+label+'_BEGIN\n')
        started = time.monotonic_ns()
        with Path('/dev/kmsg').open('w') as file:
            file.write(payload)
        elapsed_ms = (time.monotonic_ns()-started)/1e6
        trace.joinpath('trace_marker').write_text('K142_CONSOLE_'+label+'_END\n')
        samples.append(dict(label=label, ignore_loglevel=ignore, syscall_elapsed_ms=round(elapsed_ms,6),
            payload_bytes=len(payload.encode()), expected_info_retained_in_dmesg=True))
        time.sleep(0.25)
except BaseException as exc:
    error = dict(type=type(exc).__name__,message=str(exc))
finally:
    parameter.write_text(original_ignore+'\n')
    os.sched_setaffinity(0,original_affinity)
    trace.joinpath('tracing_on').write_text('0')
    out.joinpath('trace-private.txt').write_text(trace.joinpath('trace').read_text())
    stats = {p.parent.name:p.read_text() for p in trace.joinpath('per_cpu').glob('cpu*/stats')}
    out.joinpath('trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
    trace.joinpath('events/enable').write_text('0')
    trace.rmdir()
after = dmesg()
out.joinpath('dmesg-after-private.txt').write_text(after)
report = dict(stage=142, kernel_build=140, error=error, same_boot=boot_path.read_bytes()==boot,
    tests=samples, original_ignore_loglevel_restored=parameter.read_text().strip()==original_ignore,
    printk_level_unchanged=Path('/proc/sys/kernel/printk').read_text()==original_printk,
    affinity_restored=os.sched_getaffinity(0)==original_affinity,
    both_info_messages_retained_in_dmesg=all(after.count('K142 console latency '+label+' '+('x'*50))==1 for label in ['A','B']),
    own_trace_removed=not trace.exists(), counts_before=counts(before), counts_after=counts(after),
    taint=int(Path('/proc/sys/kernel/tainted').read_text()), screen_already_idle_off=True,
    no_display_or_gpu_workload_requested=True, charging_registers_not_written=True,
    functional_driver_fix_applied=False, goal_complete=False)
out.joinpath('ab-validation.json').write_text(json.dumps(report,indent=2)+'\n')
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n'
    for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar','-C',str(out),'-czf','/tmp/k142-console-latency-ab-private.tar.gz','.'],check=True,timeout=20)
print(json.dumps(report,indent=2))
