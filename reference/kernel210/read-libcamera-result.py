from pathlib import Path
import json,re
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k210-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k210-libcamera-inspection');stdout=(out/'list-stdout-private.txt').read_text();stderr=(out/'list-stderr-private.txt').read_text()
report=json.loads((out/'summary.json').read_text());report.update(camera_entries=[l.strip() for l in stdout.splitlines() if re.match(r'^\d+:',l.strip())],list_stdout=stdout,warning_error_lines=[l for l in stderr.splitlines() if 'ERROR' in l or 'WARN' in l])
(out/'summary-corrected.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
