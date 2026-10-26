"""Summarize the actual AF run; a completed failed search is not optical success."""
from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent
kind,run=sys.argv[1:3]
code='''
from pathlib import Path
import json
root=Path(ROOT)
state=json.loads((root/'state.json').read_text())
def live(pid):
 p=Path('/proc',str(pid),'stat')
 return p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':state,'worker_live':live(state['pid']),'child_live':live(state.get('child_pid',-1)),
 'logs':{p.name:p.read_text(errors='replace') for p in root.glob('*.log')}}))
'''.replace('ROOT',repr('/var/lib/samurai/k313-'+kind+'-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/(kind+'-'+run+'-results.json')).write_bytes(q.stdout)
data=json.loads(q.stdout);state=data['state']
if not state['terminal'] or data['worker_live'] or data['child_live']:
 raise SystemExit('Capture still running; inspect before analysis')
text='\n'.join(data['logs'].values())
images=[{k:float(v) if '.' in v else int(v) for k,v in re.findall(r'(\w+)=([\d.]+)',line)}
        for line in text.splitlines() if line.startswith('AF_IMAGE ')]
moves=[];active=None
for line in text.splitlines():
 m=re.search(r'Focus command serial=(\d+) position=(\d+) result=(-?\d+) at=(\d+)',line)
 if m:
  active=dict(zip(['serial','position','result','at'],map(int,m.groups())))
  active['eligible_scores']=[];moves.append(active)
 m=re.search(r'AF frame sof=(\d+) captured=(\d+) guard=(\d+) now=(\d+) valid=(\d+) score=(\d+) state=(\d+)',line)
 if m and active:
  sof,captured,guard,now,valid,score,afstate=map(int,m.groups())
  if active['result']==0 and valid and captured<=now and captured>active['at']+100000000+guard:
   active['eligible_scores'].append(score)
result=re.search(r'AF_RESULT frames=(\d+) failed=(\d+) state=(-?\d+) triggered=(\d+) scanning=(\d+) cancelled=(\d+) result=(-?\d+)',text)
end=dict(zip(['frames','failed','state','triggered','scanning','cancelled','result'],map(int,result.groups()))) if result else None
scanning=[i for i in images if i.get('state')==1]
summary={'stage':313,'kind':kind,'run':run,'capture':state.get('summary'),
 'worker_live':data['worker_live'],'child_live':data['child_live'],'result':end,
 'image_frames':len(images),'states':sorted({i.get('state',-1) for i in images}),
 'all_frames_have_focus_and_sensor_metadata':bool(images) and all(all(k in i for k in ['state','fom','exposure_us','gain','red','blue']) for i in images),
 'scanning_sensor_wb_combinations':sorted({tuple(i.get(k) for k in ['exposure_us','gain','red','blue']) for i in scanning[4:]}),
 'moves':moves,'optical_focused':bool(end and end['state']==2),
 'metric':'bounded CPU spatial contrast on hardware NV12 Y; no VFE BAF',
 'lens_range_is_not_dioptre_calibration':True,'product_installed':False}
summary['passed']=bool(state.get('summary',{}).get('passed') and end and not end['failed'] and end['result']==0 and end['scanning'] and images and summary['all_frames_have_focus_and_sensor_metadata'] and moves and all(m['result']==0 for m in moves) and (end['state'] in [2,3] if kind=='af-scan' else end['state']==0 and end['cancelled']))
(HERE/(kind+'-'+run+'-validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(0 if summary['passed'] else 1)
