from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k210-runtime/boot-id-private.txt').read_bytes()
p=Path('/var/lib/samurai/k210-static-front-capture-r2/summary.json');print(p.read_text())
print(Path('/var/lib/samurai/k210-capture-monitor-fixture/summary.json').read_text())
