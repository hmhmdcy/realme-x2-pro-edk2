"""Read completed process handles and actual per-phase image/teardown evidence."""
from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent
run=sys.argv[1]
code='''
from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
p=Path('/proc',str(s['pid']),'stat');live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':s,'worker_live':live,'logs':{p.name:p.read_text(errors='replace') for p in root.glob('*.log')},'dmesg':(root/'dmesg-after.txt').read_text(errors='replace')}))
'''.replace('ROOT',repr('/var/lib/samurai/k314-dual-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/('dual-'+run+'-results.json')).write_bytes(q.stdout)
d=json.loads(q.stdout)
if not d['state']['terminal'] or d['worker_live']:raise SystemExit('Worker still running; inspect this handle again')
summary={'stage':314,'run':run,'worker_live':False,'capture':d['state']['summary'],'sensors':{},'product_raw_handler_integrated':False}
for name,text in d['logs'].items():
 if not name.startswith('capture-'):continue
 model=name.removeprefix('capture-').removesuffix('.log')
 frames=[]
 for line in text.splitlines():
  if line.startswith('DUAL_FRAME '):
   row=dict(re.findall(r'(\w+)=([\w]+)',line));frames.append(row)
 phases={}
 for phase in range(5):
  counts={n:sum(f['node']==n and int(f['phase'])==phase for f in frames) for n in ['raw','pix']}
  required=['pix'] if phase==1 else ['raw'] if phase==3 else ['raw','pix']
  phases[str(phase)]={'counts':counts,'required_active_nodes':required,'passed':all(counts[n]>=8 for n in required)}
 # This supplements older worker schemas that missed local halt errors.
 # Include the run's following stop/unwind, which can outlast the last image.
 times=[int(f['timestamp_us'])/1000000 for f in frames]
 errors=[]
 if times:
  for line in d['dmesg'].splitlines():
   m=re.match(r'\[\s*([\d.]+)\]',line)
   if m and min(times)-1<=float(m[1]) and any(w in line for w in ['Stream stop failed:','Failed to disable stream on remote pad:','Missing SOF tag','Received wm done for unmapped index']):errors.append(line)
 stops=re.findall(r'STOP node=(\w+) epoch=(\d+) result=(-?\d+)',text)
 summary['sensors'][model]={'frames':len(frames),'phases':phases,'starts':re.findall(r'START node=(\w+) epoch=(\d+)',text),
  'stop_results':stops,'related_kernel_errors':errors,'fixture_restored':'FIXTURE_RESTORATION result=0' in text,
  'passed':'DUAL_RESULT success=1' in text and all(p['passed'] for p in phases.values()) and len(stops)==4 and all(v[2]=='0' for v in stops) and not errors}
summary['passed']=summary['capture']['passed'] and bool(summary['sensors']) and all(s['passed'] for s in summary['sensors'].values())
(HERE/('dual-'+run+'-validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'run':run,'passed':summary['passed'],'sensors':{m:{'frames':s['frames'],'passed':s['passed'],'kernel_errors':s['related_kernel_errors']} for m,s in summary['sensors'].items()}},indent=2))
raise SystemExit(0 if summary['passed'] else 1)
