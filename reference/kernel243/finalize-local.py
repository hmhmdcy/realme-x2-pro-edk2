"""Lock public sources and summarize private timelines without disclosing payloads."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
for p in R.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
spec=importlib.util.spec_from_file_location('diag243',R/'diag_transport.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
regression=m.regression();(R/'diag-parser-regression-validation.json').write_text(json.dumps(dict(stage=243,**regression),indent=2)+'\n')
a=json.loads((P/'inspect-runtime-private.json').read_text())['private']['dmesg']['stdout'];v=json.loads((P/'final-health-private.json').read_text());b=v['private']['dmesg']
v['report']['whole_stage_fault_delta']={k:b.count(t)-a.count(t) for k,t in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dsp_fatal='fatal error received').items()}
assert not any(v['report']['whole_stage_fault_delta'].values());(R/'final-health-validation.json').write_text(json.dumps(v['report'],indent=2)+'\n')
attribution=json.loads((P/'attribute-ldo10-private.json').read_text());trace=attribution['private']['trace'];attribution['report']['trace_sha256']=hashlib.sha256(trace.encode()).hexdigest()
assert not attribution['report']['failure'] and attribution['report']['trace_removed'] and attribution['report']['no_trace_overrun'] and not any(attribution['report']['fault_delta'].values())
(R/'attribute-ldo10-validation.json').write_text(json.dumps(attribution['report'],indent=2)+'\n')
rows=[json.loads(x) for x in (P/'evidence/k243-diag-query-r2/events-private.jsonl').read_text().splitlines()];timeline=[]
passive=[json.loads(x) for x in (P/'evidence/k243-diag-passive-r3/events-private.jsonl').read_text().splitlines()]
observed=next(x for x in passive if x.get('channel')=='control' and bytes.fromhex(x['hex'])[:4]==struct.pack('<I',8));peer=(observed['node'],observed['port'])
for x in rows:
 item={k:y for k,y in x.items() if k in ['kind','elapsed_ms','channel','request_code','selected_mask','remote_mask']}
 if 'hex' in x:
  raw=bytes.fromhex(x['hex'])
  if x['kind']=='response':item.update(payload_bytes=len(raw),response_code=raw[0])
  elif x['kind']=='query':item.update(request_code=raw[0])
  elif x['kind']=='rx' and len(raw)==20 and struct.unpack_from('<I',raw)[0]==6:item.update(namespace_delete_client=True,deleted_was_observed_control_peer=struct.unpack_from('<II',raw,4)==peer)
 if x['kind']!='rx' or item.get('namespace_delete_client'):timeline.append(item)
(R/'diag-timeline-validation.json').write_text(json.dumps(dict(stage=243,timeline=timeline,disconnect_causality_not_proven=True,no_gnss_measurement_logs=True),indent=2)+'\n')
dependencies=[R.parent/'kernel242/native-clock-session.py',R.parent/'kernel242/analyze-clock-session.py',R.parent/'kernel226/loc_decode.py',R.parent/'kernel208/pqwm1.py',R.parent/'kernel240/host.py']
lock=dict(stage=243,local_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.suffix in ['.py','.c']},dependencies={str(p.relative_to(R.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},diag_upstream_commit=subprocess.check_output(['git','-C',str(P/'diag-upstream'),'rev-parse','HEAD'],text=True).strip(),deployed_libraries=json.loads((R/'collect-deployed-sources-validation.json').read_text())['deployed_library_sha256'])
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
(P/'current-checkpoint-private.json').write_text(json.dumps(dict(stage=243,health=v['report'],gnss_fixed=False,android_booted=False,diag_measurement_capture=False,worker_active=False,raw_evidence_members=110,wlan_test_restored=True,idle_ldo10_attributed_to_ufs=True),indent=2)+'\n')
print(json.dumps(dict(stage=243,compiled_python_sources=len(list(R.glob('*.py'))),locked_local_sources=len(lock['local_sources']),whole_stage_fault_delta=v['report']['whole_stage_fault_delta'],regression=regression)))
