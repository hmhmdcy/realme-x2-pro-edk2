"""Adapt the verified state-restoring worker to one controlled timing epoch."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300'
s=(OLD/'native-ipa.py').read_text().replace('k300-ipa','k301-delay').replace('stage=300','stage=301')
anchor="str(stage/'bin/pipeline-smoke'),'imx319']";assert s.count(anchor)==1
s=s.replace(anchor,"str(stage/'bin/pipeline-smoke'),'imx319',str(stage/'bin/control-stepper')]")
anchor=" report['passed']=ret==0";start=s.index(anchor);end=s.index(" (root/'summary-private.json').write_text",start)
s=s[:start]+r'''
 events=[dict(sof=int(a),pending=int(b),event_ns=int(c),observed_ns=int(d)) for a,b,c,d in re.findall(r'STEPPER_SOF sequence=(\d+) pending=(\d+) event_ns=(\d+) observed_ns=(\d+)',text)]
 writes=[dict(step=int(a),sof=int(b),id=int(c),value=int(d),event_ns=int(e),begin_ns=int(f),end_ns=int(g),ret=int(h),errno=int(i)) for a,b,c,d,e,f,g,h,i in re.findall(r'CONTROL_WRITE step=(\d+) sof=(\d+) id=(\d+) value=(\d+) event_ns=(\d+) begin_ns=(\d+) end_ns=(\d+) ret=(-?\d+) errno=(\d+)',text)]
 stepper_pids=set(map(int,re.findall(r'STEPPER_READY pid=(\d+)',text)))
 stepper_live=[]
 for pid in stepper_pids:
  p=Path('/proc',str(pid),'cmdline')
  if p.exists() and str(stage/'bin/control-stepper').encode() in p.read_bytes():stepper_live.append(pid)
 report.update(sof_events=events,control_writes=writes,stepper_pids=sorted(stepper_pids),stepper_still_live=stepper_live,
  measurement_only_no_delayed_controls_or_ae_implementation=True)
 process_mode_ok=len(app_pids)==1 and len(ipa_pids)==1 and stats_pids==ipa_pids and ((force=='1' and not app_pids.intersection(ipa_pids)) or (force=='0' and app_pids==ipa_pids and 'signature is valid' in text))
 expected_sofs=[12,36,60,84,108,132,156,180,204]
 report['passed']=(ret==0 and len(epochs)==1 and epochs[0]['frames']>=240 and not epochs[0]['failed'] and not epochs[0]['stop']
  and len(applied)==1 and applied[0]['first_sof']==0 and set(p['epoch'] for p in pairs)=={1}
  and len(pairs)==report['application_frames']==report['ipa_metadata_frames'] and len(pairs)>=240
  and len(set(p['sof'] for p in pairs))==len(pairs) and len(set(p['request'] for p in pairs))==len(pairs)
  and report['graph_restored'] and before==after and not any(faults.values()) and 'FIXTURE_RESULT result=0' in text
  and process_mode_ok and not ipa_live and not stepper_live and len(stepper_pids)==1
  and [e['sof'] for e in events]==list(range(233)) and not any(e['pending'] for e in events)
  and [w['sof'] for w in writes]==expected_sofs and not any(w['ret'] or w['errno'] for w in writes)
  and 'STEPPER_INITIAL_READBACK exposure=500 gain_code=512' in text and 'STEPPER_RESULT result=0 events=233 steps=9' in text)
'''+s[end:]
ast.parse(s);(HERE/'native-delay.py').write_text(s)
s=(OLD/'launch-ipa.py').read_text().replace('k300-ipa','k301-delay').replace('ipa-bundle-validation','delay-bundle-validation').replace('native-ipa.py','native-delay.py').replace("f'ipa-{run}-launch","f'delay-{run}-launch")
ast.parse(s);(HERE/'launch-delay.py').write_text(s)
s=(OLD/'poll-ipa.py').read_text().replace('k300-ipa','k301-delay').replace("f'ipa-{run}-poll","f'delay-{run}-poll")
start=s.index(" (HERE/'ipa-capture-validation.json')");end=s.index("summary=report.get",start)
s=s[:start]+''' summary=report['summary'];public={k:v for k,v in summary.items() if k not in ['exact_sof_pairs','sof_events','control_writes']}
 public.update(exact_sof_pairs_count=len(summary['exact_sof_pairs']),observed_sof_count=len(summary['sof_events']),control_write_count=len(summary['control_writes']))
 (HERE/f'delay-capture-{run}-validation.json').write_text(json.dumps(public,indent=2)+'\\n')
'''+s[end:]
s=s.replace("['before','after','exact_sof_pairs']","['before','after','exact_sof_pairs','sof_events','control_writes']")
ast.parse(s);(HERE/'poll-delay.py').write_text(s)
print('Prepared bounded measurement worker, launch and terminal poll. No phone operation.')
