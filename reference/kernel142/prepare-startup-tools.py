"""Prepare another same-kernel observation with IRQ/idle events and early launch."""
from pathlib import Path
import ast
import hashlib
import json

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel142'
base = root / 'reference/kernel141'
out = Path('/mnt/e/edk2-samurai-out/kernel142')
assert not out.exists() and not (ref / 'collect-preflash.sh').exists()
previous = json.loads((base / 'settled-health-validation.json').read_text())
assert previous['current_kernel'] == 140 and previous['archive_hash_verified'] and previous['counters_unchanged']
out.mkdir(mode=0o700)
bundle = json.loads((base / 'current140-build-package-validation.json').read_text())
assert bundle['actual_runtime_verified'] and bundle['kernel_build'] == 140
for record in bundle['artifacts']:
    path = Path(record['artifact_path'])
    assert path.stat().st_size == record['bytes']
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024**2):
            digest.update(chunk)
    assert digest.hexdigest() == record['sha256']
bundle.update(stage=142, same_current140_kernel_reboot_only=True,
              four_artifacts_fresh_hash_verified=True, partitions_to_write=[],
              temporary_early_recording_service_planned=True)
for folder in [ref, out]:
    (folder / 'current140-build-package-validation.json').write_text(json.dumps(bundle, indent=2) + '\n')

def adapt(name):
    return (base / name).read_text().replace('kernel141', 'kernel142').replace('k141', 'k142').replace('K141', 'K142').replace('stage=141', 'stage=142')

def write(name, text):
    assert not (ref / name).exists()
    if name.endswith('.py'):
        ast.parse(text)
    (ref / name).write_text(text)

text = adapt('collect-preflash.sh').replace('/var/lib/samurai/k140-first-runtime/boot-id-private.txt', '/var/lib/samurai/k141-first-runtime/boot-id-private.txt')
write('collect-preflash.sh', text)
text = adapt('verify-preflash.py').replace("out.parent / 'kernel140/embedded-boot-id-private.txt'", "out.parent / 'kernel141/embedded-boot-id-private.txt'")
write('verify-preflash.py', text)
for name in ['quiesce-current140.sh', 'verify-quiesce.py', 'freeze-for-bootloader.sh',
             'collect-runtime.sh', 'verify-runtime.py', 'check-new-boot.py', 'observe-settled-health.py']:
    write(name, adapt(name))
for name in ['enable-transition-eud.ps1', 'enter-bootloader.ps1', 'reboot-same140-fastboot.ps1', 'poll-new-boot.ps1']:
    write(name, adapt(name).replace('startup-first', 'irq-first'))
text = adapt('capture-next-startup.py')
text = text.replace('import subprocess\n', 'import subprocess\nimport threading\nimport select\n')
text = text.replace("(trace / 'buffer_size_kb').write_text('8192')", "(trace / 'buffer_size_kb').write_text('16384')")
text = text.replace("trace.mkdir()\n", """events += [('irq', n) for n in ['irq_handler_entry', 'irq_handler_exit', 'softirq_entry', 'softirq_exit']]
events += [('power', n) for n in ['cpu_idle', 'cpu_frequency', 'cpu_frequency_limits',
    'suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end']]
events += [('timer', n) for n in ['timer_expire_entry', 'timer_expire_exit']]
trace.mkdir()
reader_stop = threading.Event()
reader_errors = []
reader = None

def drain_pipe():
    fd = None
    try:
        fd = os.open(trace / 'trace_pipe', os.O_RDONLY | os.O_NONBLOCK)
        with (out / 'startup-stream-private.txt').open('wb') as stream:
            while not reader_stop.is_set():
                ready, _, _ = select.select([fd], [], [], 0.2)
                if not ready:
                    continue
                try:
                    chunk = os.read(fd, 262144)
                except BlockingIOError:
                    continue
                if chunk:
                    stream.write(chunk)
            while True:
                try:
                    chunk = os.read(fd, 262144)
                except BlockingIOError:
                    break
                if not chunk:
                    break
                stream.write(chunk)
    except BaseException as exc:
        reader_errors.append(dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if fd is not None:
            os.close(fd)

""")
text = text.replace("    (trace / 'tracing_on').write_text('1')\n", "    reader = threading.Thread(target=drain_pipe, name='trace-reader')\n    reader.start()\n    (trace / 'tracing_on').write_text('1')\n")
text = text.replace('K142_POST_SSH_STARTUP_CAPTURE_BEGIN', 'K142_EARLY_BOOT_IRQ_IDLE_CAPTURE_BEGIN')
text = text.replace("            active='active=1' in Path('/sys/kernel/debug/dri/1/state').read_text())", "            active=Path('/sys/kernel/debug/dri/1/state').is_file() and 'active=1' in Path('/sys/kernel/debug/dri/1/state').read_text())")
text = text.replace("    (trace / 'tracing_on').write_text('0')\n    capture(['cat', str(trace / 'trace')],", "    (trace / 'tracing_on').write_text('0')\n    reader_stop.set()\n    if reader is not None:\n        reader.join(timeout=5)\n        assert not reader.is_alive(), 'trace reader did not stop'\n    capture(['cat', str(trace / 'trace')],")
text = text.replace('error=error, sample_count=', "error=error, trace_stream_reader_errors=reader_errors, early_boot_service=True, sample_count=")
text = text.replace('physical_pixel_visibility_not_verified=True, goal_complete=False)', 'physical_pixel_visibility_not_verified=True, instrumentation_may_change_timing=True, goal_complete=False)')
assert 'stage=142' in text and "version.startswith('#140 ')" in text
assert 'trace_stream_reader_errors' in text and 'early_boot_service=True' in text
write('capture-next-startup.py', text)
print('K142_SAME140_EARLY_STARTUP_IRQ_IDLE_STREAMING_TOOLS_READY')
