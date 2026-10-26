"""Offline fixtures only; no device or real /proc/sys access."""
from pathlib import Path
import importlib.util
import json
import struct
import tempfile
import zlib

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('inventory', here / 'read-only-inventory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def frame(records, first=1):
    count = len(records)
    last = first + count - 1 if count else 0
    header = struct.pack('<8sIIIIQQII', b'EUDTXJ48', 1, 48 + 6 * count,
                         count, 6, first if count else 0, last, 0, 0)
    data = bytearray(header + b''.join(struct.pack('<BB4s', *r) for r in records))
    struct.pack_into('<I', data, 40, zlib.crc32(data))
    return bytes(data)


checks = 0
good = frame([(4, 2, b'ABCD'), (1, 1, b'X\0\0\0')], 900)
summary = module.journal_summary(good)
assert summary['first_frame_seq'] == 900 and summary['last_frame_seq'] == 901
assert summary['tail_by_source'] == {'console': {'frames': 1, 'bytes': 4},
                                     'tty': {'frames': 1, 'bytes': 1}}
checks += 2
assert module.journal_summary(frame([]))['retained_frames'] == 0
checks += 1
invalid = [b'', good[:47], good[:-1], good + b'\0',
           bytes([good[0] ^ 1]) + good[1:],
           good[:-1] + bytes([good[-1] ^ 1]),
           frame([(0, 2, b'\0' * 4)]), frame([(4, 3, b'\0' * 4)])]
for item in invalid:
    try:
        module.journal_summary(item)
    except ValueError:
        checks += 1
    else:
        raise AssertionError('Accepted bad journal')
with tempfile.TemporaryDirectory(prefix='inventory-fixture-', dir=here) as directory:
    root = Path(directory)
    def put(name, data):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
    put('proc/cmdline', 'root=PRIVATE console=eud earlycon=eud,0x88e0000 no_console_suspend secret=PRIVATE')
    put('proc/consoles', 'eud0 -W- (EC p a)  0:0\n')
    put('sys/bus/platform/devices/88e0000.serial/tx_journal', good)
    put('sys/kernel/tracing/available_events', 'sched:sched_switch\nprintk:console\nprivate:other\n')
    put('sys/kernel/tracing/events/sched/sched_switch/trigger', '# Available triggers: stacktrace traceon\n')
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = module.inventory(root, 123)
    assert result['cmdline_console_tokens_only'] == ['console=eud', 'earlycon=eud,0x88e0000', 'no_console_suspend']
    assert result['selected_available_events'] == ['printk:console', 'sched:sched_switch']
    assert result['eud_tx_journal'] == summary
    assert result['selected_process']['stack']['error'] == 'FileNotFoundError'
    assert result['sched_stacktrace_trigger_catalog'].startswith('# Available triggers: stacktrace')
    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert before == after
    checks += 6
report = {'fixture_assertions': checks, 'phone_accessed': False,
          'live_trace_armed': False, 'fixture_files_unchanged_after_inventory': True}
(here / 'inventory-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
