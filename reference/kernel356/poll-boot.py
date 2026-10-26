from pathlib import Path
import json,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k356-boot-RUN');state=json.loads((root/'state.json').read_text());proc=Path('/proc')/str(state['pid'])
state['worker_process_observed']=proc.exists() and str(root/'worker.py').encode() in (proc/'cmdline').read_bytes()
print(json.dumps(state))
'''.replace('RUN',run)
q=host.raw_ssh('python3 -',input=code.encode(),timeout=20);state=json.loads(q.stdout);(P/('probe-'+run+'-observation-private.json')).write_text(json.dumps(state,indent=2)+'\n')
if state['terminal']:
 keys=['terminal','worker_process_observed','device_result','clocks_before','clocks_after','camss_before','camss_after','core_absent','test_absent','temporary_dt_nodes_absent','temporary_firmware_removed','taint_before','taint_after','passed','error','cleanup_error','requires_cleanup_attention']
 report=dict(stage=356,run=run,**{k:state[k] for k in keys if k in state},new_relevant_fault_count=len(state['new_relevant_faults']),persistent_dt_or_installed_modules_changed=False)
 for name in ['boot-runtime-validation.json','boot-runtime-'+run+'-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:print(json.dumps(dict(terminal=False,phase=state['phase'],worker_process_observed=state['worker_process_observed'])))
