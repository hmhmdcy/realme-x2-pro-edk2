from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k243-diag-passive-r3';rows=[json.loads(x) for x in (p/'events-private.jsonl').read_text().splitlines()]
lookup=subprocess.check_output(['qrtr-lookup']).decode();services=[line.split()[:5] for line in lookup.splitlines() if line.split() and line.split()[0]=='4097']
report=dict(stage=243,cleanup=rows[-1],remaining_diag_services=services,read_only_followup=True)
print(json.dumps(dict(report=report,private=dict(records=rows,lookup=lookup,summary=json.loads((p/'summary.json').read_text())))))
