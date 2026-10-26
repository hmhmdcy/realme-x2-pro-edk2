from pathlib import Path
import json,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k354-memory-r1');state=json.loads((root/'state.json').read_text());pid=state['pid'];proc=Path('/proc')/str(pid)
state['worker_process_observed']=proc.exists() and str(root/'worker.py').encode() in (proc/'cmdline').read_bytes()
print(json.dumps(state))
'''
code=code.replace('/var/lib/samurai/k354-memory-r1','/var/lib/samurai/k354-memory-'+run)
q=host.raw_ssh('python3 -',input=code.encode(),timeout=20);state=json.loads(q.stdout);(P/('probe-'+run+'-observation-private.json')).write_text(json.dumps(state,indent=2)+'\n')
if state['terminal']:
 report=dict(stage=354,run=run,terminal=True,worker_process_observed=state['worker_process_observed'],device_result={k:v for k,v in state.get('device_result',{}).items() if k!='backing_dma'},
  icp_leaf_clock_enable_counts=state.get('icp_leaf_clock_enable_counts'),core_absent=state['core_absent'],test_absent=state['test_absent'],temporary_dt_nodes_absent=state['temporary_dt_nodes_absent'],
  taint_before=state['taint_before'],taint_after=state['taint_after'],new_relevant_fault_count=len(state['new_relevant_faults']),
  firmware_started=False,persistent_dt_or_installed_modules_changed=False,passed=state['passed'])
 if 'error' in state:report['error']=state['error']
 for name in ['memory-runtime-validation.json','memory-runtime-'+run+'-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:print(json.dumps(dict(terminal=False,phase=state['phase'],worker_process_observed=state['worker_process_observed'])))
