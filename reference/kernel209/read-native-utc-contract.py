from pathlib import Path
import host,json
target=host.PRIVATE/'qmi-enums-loc-current-private.h'
host.download('/var/lib/samurai/k190-mm-sdk/usr/include/libqmi-glib/qmi-enums-loc.h',target)
text=target.read_text()
lines=text.splitlines();start=next(i for i,line in enumerate(lines) if 'QmiLocInjectedTimeSource:' in line)
print('\n'.join(lines[start:start+25]))
native="from pathlib import Path; import json; root=Path('/var/lib/samurai'); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes(); watch=json.loads((root/'k209-clock-compare/watch-after-private.json').read_text()); print(json.dumps(dict(last_result=watch['last_result'],worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'])))"
p=host.ssh('python3 -',input=native.encode(),timeout=25)
(host.PRIVATE/'automatic-worker-after-comparison-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
