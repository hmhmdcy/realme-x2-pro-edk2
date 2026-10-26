"""PC-only targeted inspection of the existing k363 build and trace sources."""
from pathlib import Path
import hashlib
import json
import re
import sys

sys.path.insert(0, '/mnt/e/RealmeX2Pro edk2/reference/kernel284')
import storage
build = storage.mounted_build()
source = build.parent / 'source354'
root = Path(__file__).resolve().parent / 'trace-plan'
root.mkdir(exist_ok=True)
config_text = (build / '.config').read_text()
symbols = ('FTRACE', 'FUNCTION_TRACER', 'FUNCTION_GRAPH_TRACER', 'DYNAMIC_FTRACE',
    'EVENT_TRACING', 'TRACING', 'TRACING_SUPPORT', 'KPROBES', 'KPROBE_EVENTS',
    'FPROBE', 'FPROBE_EVENTS', 'SCHED_TRACER', 'STACKTRACE', 'IRQSOFF_TRACER',
    'RCU_TRACE', 'SRCU', 'TREE_SRCU', 'DEBUG_LOCK_ALLOC', 'LOCKDEP', 'LOCK_STAT',
    'PREEMPT_TRACER', 'PRINTK', 'PRINTK_TIME', 'PM_DEBUG', 'PM_SLEEP_DEBUG')
config = {}
for symbol in symbols:
    m = re.search(r'^CONFIG_' + symbol + r'=(.*)$', config_text, re.M)
    config['CONFIG_' + symbol] = m[1] if m else 'n' if f'# CONFIG_{symbol} is not set' in config_text else 'absent'
files = ('include/trace/events/printk.h', 'include/trace/events/power.h',
    'include/trace/events/irq.h', 'include/trace/events/rcu.h', 'include/trace/events/lock.h',
    'include/trace/events/rtc.h', 'drivers/rtc/trace.h',
    'kernel/trace/trace_functions_graph.c', 'kernel/trace/fgraph.c')
manifest = {}
for name in files:
    p = source / name
    if not p.exists():
        manifest[name] = {'exists': False}
        continue
    data = p.read_bytes()
    assert len(data) < 300000
    (root / name.replace('/', '--')).write_bytes(data)
    manifest[name] = {'exists': True, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
targets = {'console_suspend_all', '__pr_flush', 'pr_flush', 'console_lock',
           'console_unlock', 'console_list_lock', 'synchronize_srcu'}
present = []
mapfile = build / 'System.map'
if mapfile.exists():
    with mapfile.open() as f:
        for line in f:
            fields = line.split()
            if len(fields) >= 3 and fields[2] in targets:
                present.append(fields[2])
report = {'kernel_release': (build / 'include/config/kernel.release').read_text().strip(),
    'config_sha256': hashlib.sha256((build / '.config').read_bytes()).hexdigest(),
    'config': config, 'target_symbols_in_existing_System_map': sorted(present),
    'runtime_available_functions_not_observed': True, 'files': manifest,
    'phone_accessed': False, 'shared_source_or_config_modified': False}
(root / 'capabilities.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
