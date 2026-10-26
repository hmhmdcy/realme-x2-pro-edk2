"""Read actual completed requests, SOF correlations and resource restoration."""
from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1]
code='''
from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text())
p=Path('/proc',str(state['pid']),'stat');live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':state,'worker_live':live,'logs':{p.name:p.read_text(errors='replace') for p in root.glob('*.log')},'dmesg':(root/'dmesg-after.txt').read_text(errors='replace')}))
'''.replace('ROOT',repr('/var/lib/samurai/k315-raw-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/('raw-'+run+'-results.json')).write_bytes(q.stdout)
d=json.loads(q.stdout)
if not d['state']['terminal'] or d['worker_live']:raise SystemExit('Worker still running; inspect this same handle')
report=dict(stage=315,run=run,capture=d['state']['summary'],worker_live=False,selections={},installed=False)
for name,text in d['logs'].items():
 if not name.startswith('capture-'):continue
 label=name.removeprefix('capture-').removesuffix('.log');model,kind=label.rsplit('-',1)
 pairs=[]
 for line in text.splitlines():
  if ' RawPair request=' in line:
   row=dict(re.findall(r'([\w-]+)=(\d+)',line));pairs.append({k:int(v) for k,v in row.items()})
 result=re.search(r'RAW_RESULT model=(\w+) kind=(\w+) frames=(\d+) stable=(\d+) failed=(\d+) result=(\d+)',text)
 images=re.findall(r'^RAW_IMAGE (.*)$',text,re.M)
 errors=[line for line in text.splitlines() if any(t in line for t in ['Frame sync event missing','ERROR ','ERROR:','assertion ', 'Frame sync mismatch'])]
 formats=sorted(set(re.findall(r'format=(\w+)', '\n'.join(images))))
 item=dict(model=model,kind=kind,images=len(images),formats=formats,paired_requests=len(pairs),
  mismatched_requests=sum(not p['matched'] for p in pairs),
  max_pair_delta_ns=max((p['delta-ns'] for p in pairs),default=None),
  min_pair_delta_ns=min((p['delta-ns'] for p in pairs),default=None),
  different_line_sequences=sum(p['pix-sof']!=p['raw-sof'] for p in pairs),
  fixture_restored='FIXTURE_RESTORATION result=0' in text,errors=errors)
 if result:item.update(frames=int(result[3]),stable=int(result[4]),failed=int(result[5]),result=int(result[6]))
 if kind.startswith('af'):
  final=re.search(r'af-state=(\d+) af-triggered=(\d+) af-scanning=(\d+) af-cancelled=(\d+)',text)
  item['af']={k:int(final[i+1]) for i,k in enumerate(['state','triggered','scanning','cancelled'])} if final else {}
  item['lens_commands']=len(re.findall(r'Focus command serial=',text))
  item['lens_errors']=re.findall(r'Focus command serial=.*result=(-?[1-9]\d*)',text)
 if kind=='hold':
  item['buffer_hold_observed']='RAW_BUFFER_HOLD count=4' in text and 'RAW_BUFFER_RESUME' in text
  sequences=[p['pix-sof'] for p in pairs]
  item['unreturned_frame_slots']=sum(max(0,b-a-1) for a,b in zip(sequences,sequences[1:]))
 item['passed']=bool(result) and not item['result'] and not item['failed'] and item['fixture_restored'] and not errors and (kind=='pix' or len(pairs)==item['frames'] and all(p['matched'] for p in pairs))
 if kind.startswith('af'):item['passed'] &= bool(item['af']) and item['af']['triggered']==1 and item['af']['scanning']==1 and item['af']['state']==(0 if kind=='afcancel' else 2) and not item['lens_errors']
 if kind=='hold':item['passed'] &= item['buffer_hold_observed'] and item['unreturned_frame_slots']>0
 report['selections'][label]=item
report['passed']=report['capture']['passed'] and bool(report['selections']) and all(v['passed'] for v in report['selections'].values())
(HERE/('raw-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
