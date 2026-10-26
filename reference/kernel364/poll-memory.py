from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;name=sys.argv[1];assert re.fullmatch(r'r[1-9][0-9]*',name)
code=r'''
from pathlib import Path
import json
root=Path(ROOT);d=json.loads((root/'state.json').read_text());p=Path('/proc',str(d['pid']));live=False
try:live=str(root/'worker.py').encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
except OSError:pass
print(json.dumps(dict(state=d,worker_live=live)))
'''.replace('ROOT',repr('/var/lib/samurai/k364-memory-'+name))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(host.PRIVATE/('memory-observation-'+name+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout);state=d['state']
if not state['terminal']:print(json.dumps(dict(phase=state['phase'],worker_live=d['worker_live'])));raise SystemExit(0)
device=dict(state['device_result']);device.pop('backing_dma',None)
report=dict(stage=364,run=name,worker_live=d['worker_live'],device=device,new_relevant_fault_count=len(state['new_relevant_faults']),taint_before=state['taint_before'],taint_after=state['taint_after'],
 core_absent=state['core_absent'],test_absent=state['test_absent'],temporary_dt_nodes_absent=state['temporary_dt_nodes_absent'],firmware_started=False,passed=state['passed'] and not d['worker_live'])
(HERE/('memory-runtime-'+name+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
