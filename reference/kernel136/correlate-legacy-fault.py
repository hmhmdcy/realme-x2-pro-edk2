from pathlib import Path
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
parsed = json.loads((out / 'legacy-vm-operations-private.json').read_text())
assert len(parsed['cores']) == 1
core = parsed['cores'][0]
ops = core['all_matching_operations']
assert len(ops) == 2
assert ops[0]['pid'] == ops[1]['pid'] and ops[0]['ttbr'] == ops[1]['ttbr']
assert ops[0]['start'] == ops[1]['start'] and ops[0]['size'] == ops[1]['size']
pid = ops[0]['pid']
ttbr = ops[0]['ttbr']
t = (out / 'submission-trace-private.txt').read_text()
d = (out / 'dmesg-final-private.txt').read_text()
c = (out / core['name']).read_text()
events = []
for line in t.splitlines():
    match = re.search(r'([0-9.]+): (msm_gpu_submit(?:_flush|_retired)?): (.*)',line)
    if match:
        item = dict(time=float(match[1]),event=match[2],fields=match[3])
        events.append(item)
(out / 'submission-events-private.json').write_text(json.dumps(events,indent=2))
faults = []
for line in d.splitlines():
    if 'gpu fault:' in line:
        time = float(re.search(r'^\[\s*([0-9.]+)\]',line)[1])
        m = re.search(r'TTBR0=(?:0x)?([0-9a-fA-F]+)',line,re.I)
        faults.append(dict(time=time,ttbr_match=bool(m and int(m[1],16)==ttbr)))
fault_info = re.search(r'^fault-info:\n(.*?)(?=^[a-z]|\Z)',c,re.S|re.M)
core_ttbr = re.search(r'ttbr0=(?:0x)?([0-9a-fA-F]+)',fault_info[1],re.I)
candidate_retired = [e for e in events if e['event']=='msm_gpu_submit_retired' and e['time'] < ops[1]['time']]
switches = [s for s in parsed['switches'] if s['pid']==pid and s['ttbr']==ttbr]
last_switch = switches[-1] if switches else None
record = dict(stage=136,
    fault_address_has_successful_map=True,
    same_vm_fault_address_later_unmapped_on_close=True,
    matching_map_ret=ops[0]['ret'],mapping_bytes=ops[0]['size'],
    map_seconds=ops[0]['time'],close_seconds=ops[1]['time'],
    fault_times=[f['time'] for f in faults],
    dmesg_fault_ttbr_matches_probe_vm=[f['ttbr_match'] for f in faults],
    core_fault_ttbr_matches_probe_vm=bool(core_ttbr and int(core_ttbr[1],16)==ttbr),
    delay_close_to_first_fault_seconds=round(faults[0]['time']-ops[1]['time'],6) if faults else None,
    last_probe_vm_switch_seconds=last_switch['time'] if last_switch else None,
    last_probe_vm_switch_seq=last_switch['seq'] if last_switch else None,
    retired_events_before_close=len(candidate_retired),
    need_decode_last_submit_and_pt_switch=True,
    address_lifecycle_identified=True,root_cause_proven=False,gpu_fix_accepted=False,goal_complete=False)
(ref / 'legacy-fault-correlation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
# Schema details without raw addresses or process IDs.
print('CORE_FAULT_KEYS', re.sub(r'=\S+', '=<private>',fault_info[1]).strip())
print('TRACE_EVENT_FIELD_KEYS', sorted(set(re.sub(r'=\S+', '=<private>',e['fields']) for e in events)))
