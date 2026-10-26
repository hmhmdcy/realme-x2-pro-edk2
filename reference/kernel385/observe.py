"""Poll the existing transaction and print a compact authoritative snapshot."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent;run=sys.argv[1] if len(sys.argv)>1 else 'r1'
q=subprocess.run([sys.executable,str(HERE/'poll-boot.py'),run],capture_output=True)
if q.returncode:
 print(q.stderr.decode(errors='replace'));raise SystemExit(q.returncode)
d=json.loads(q.stdout);r=d.get('device_result',{})
print(json.dumps(dict(run=run,terminal=d.get('terminal'),phase=d.get('phase'),passed=d.get('passed'),
 worker_live=d.get('worker_live'),collector_live=d.get('collector_live'),same_boot=d['same_boot'],
 frames=r.get('frames_completed'),width=r.get('test_width'),height=r.get('test_height'),port=r.get('test_port'),
 cores=r.get('test_cores'),uv_swap=r.get('test_uv_swap'),error=r.get('error'),cleanup_error=r.get('cleanup_error'),
 taint_after=d.get('taint_after'),new_faults=d.get('new_relevant_fault_count'),
 resources_removed=all(d.get(k) for k in ['core_absent','test_absent','temporary_dt_nodes_absent','temporary_firmware_removed'])),indent=2))
