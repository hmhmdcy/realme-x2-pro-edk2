from pathlib import Path
import json
import os

base = Path('/var/lib/samurai/k145-pre-reboot')
dest = Path('/var/lib/samurai/k145-first145-startup')
assert os.uname().version.startswith('#145 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() != Path('/var/lib/samurai/k145-preflash/boot-id-private.txt').read_bytes()
pidfile = Path('/run/k145-startup-trace.pid')
live = False
state = None
if pidfile.is_file():
    pid = int(pidfile.read_text().strip())
    process = Path('/proc') / str(pid)
    try:
        cmdline = (process / 'cmdline').read_bytes()
        status = (process / 'status').read_text()
        state = next(line.split()[1] for line in status.splitlines() if line.startswith('State:'))
        live = bytes(str(base / 'capture-next-startup.py'), 'utf8') in cmdline and state not in ['Z', 'X']
    except FileNotFoundError:
        pass
archive = Path('/tmp/k145-first145-startup-private.tar.gz')
result = json.loads((dest / 'startup-result.json').read_text()) if (dest / 'startup-result.json').is_file() else None
samples = json.loads((dest / 'startup-samples-private.json').read_text()) if (dest / 'startup-samples-private.json').is_file() else []
report = dict(new145_boot_verified=True, recorder_process_live=live, process_state=state,
    trace_instance_present=Path('/sys/kernel/tracing/instances/k145-startup').exists(),
    completed_marker=(dest / 'complete-private.txt').is_file(), archive_present=archive.is_file(),
    archive_bytes=archive.stat().st_size if archive.is_file() else None,
    samples=len(samples), last_elapsed_seconds=samples[-1]['elapsed_seconds'] if samples else None,
    last_counts=samples[-1]['counts'] if samples else None,
    terminal=not live and result is not None and archive.is_file() and (dest / 'complete-private.txt').is_file(),
    result=result)
print(json.dumps(report, indent=2))
