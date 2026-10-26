from pathlib import Path
import json
import host

R = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()
receipt=root/'k234-tools/exit-private.json'
if receipt.exists():
 result=json.loads(receipt.read_text())
 summary=root/'k234-diagnostic/summary.json'
 if summary.exists():result['summary']=json.loads(summary.read_text())
 print(json.dumps(result))
else:
 marker=json.loads((root/'k234-tools/worker-started-private.json').read_text())
 stat=Path('/proc',str(marker['pid']),'stat')
 running=stat.exists() and stat.read_text().split()[21]==marker['start_ticks']
 print(json.dumps(dict(running=running,terminal_receipt=False)))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=20)
(host.PRIVATE / 'diagnostic-poll-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
if 'exit_code' in report:
    (R / 'diagnostic-native-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    for name in ['dmesg-before-private.txt', 'dmesg-candidate-private.txt', 'dmesg-after-private.txt',
                 'uart-trace-private.txt', 'trace-stats-private.json', 'summary.json']:
        host.download('/var/lib/samurai/k234-diagnostic/' + name, host.PRIVATE / name)
    host.download('/var/lib/samurai/k234-tools/worker-private.log', host.PRIVATE / 'worker-private.log')
    state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
    state.update(active_native_worker=None, last_diagnostic_exit_code=report['exit_code'])
    (host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
