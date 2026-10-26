from pathlib import Path
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
p = json.loads((out / 'legacy-vm-operations-private.json').read_text())
assert len(p['cores']) == 1
core = p['cores'][0]
t = (out / 'submission-trace-private.txt').read_text()
d = (out / 'dmesg-final-private.txt').read_text()
c = (out / core['name']).read_text()
info = re.search(r'^fault-info:\n(.*?)(?=^[a-z]|\Z)', c,re.S|re.M)[1]
print('CORE_FAULT_KEYS', re.sub(r'=\S+', '=<private>',info).strip())
ttbrs = re.findall(r'ttbr0[=:]\s*(?:0x)?([0-9a-fA-F]+)', info,re.I)
faults = []
for line in d.splitlines():
    if 'gpu fault:' in line:
        timestamp = float(re.search(r'^\[\s*([0-9.]+)\]',line)[1])
        ttbr_match = re.search(r'ttbr0[=:]\s*(?:0x)?([0-9a-fA-F]+)',line,re.I)
        faults.append(dict(time=timestamp,ttbr=int(ttbr_match[1],16) if ttbr_match else None))
ttbr = int(ttbrs[0],16) if ttbrs else faults[0]['ttbr']
assert ttbr is not None, 'Fault VM identity must be available before correlating numeric IOVAs'
addr = core['fault_iova']
matching = [m for m in p['maps'] if m['ttbr']==ttbr and m['start']<=addr<m['start']+m['size']]
same_vm = [m for m in p['maps'] if m['ttbr']==ttbr]
events = []
for line in t.splitlines():
    match = re.search(r'([0-9.]+): (msm_gpu_submit(?:_flush|_retired)?): (.*)',line)
    if match:
        events.append(dict(time=float(match[1]),event=match[2],fields=match[3]))
switches = [s for s in p['switches'] if s['ttbr']==ttbr]
details = dict(faults=faults,ttbr=ttbr,matching_ops=matching,same_vm_ops=same_vm,
               switches=switches,events=events)
(out / 'legacy-correlation-private.json').write_text(json.dumps(details,indent=2))
record = dict(stage=136,fault_vm_identity_available=True,
    numeric_iova_matches_other_vms=len(core['all_matching_operations'])-len(matching),
    fault_vm_matching_operations=[{k:v for k,v in m.items() if k in ['op','time','size','ret']} for m in matching],
    fault_vm_total_operations=len(same_vm),
    fault_vm_switches=[{k:v for k,v in s.items() if k in ['time','ring','seq','old_ctx','new_ctx']} for s in switches],
    fault_times=[f['time'] for f in faults],
    fault_vm_ttbr_matches_all_faults=all(f['ttbr']==ttbr for f in faults),
    root_cause_proven=False,gpu_fix_accepted=False,goal_complete=False)
(ref / 'legacy-fault-correlation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
print('TRACE_EVENT_FIELD_KEYS', sorted(set(re.sub(r'=\S+', '=<private>',e['fields']) for e in events)))
