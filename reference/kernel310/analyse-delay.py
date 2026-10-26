"""Measure optical response without imposing a sensor delay in the pipeline."""
from pathlib import Path
import json,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent
run=sys.argv[1] if len(sys.argv)>1 else 'r1'
code=r'''
from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text())
p=Path('/proc',str(state['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':state,'worker_live':live,'logs':{p.stem.removeprefix('capture-'):p.read_text(errors='replace') for p in root.glob('capture-*.log')}}))
'''.replace('ROOT',repr('/var/lib/samurai/k310-delay-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
(host.PRIVATE/('delay-'+run+'-results.json')).write_bytes(q.stdout)
data=json.loads(q.stdout)
if not data['state']['terminal'] or data['worker_live']:raise RuntimeError('Measurement worker is still running; inspect the same run')
report={'stage':310,'run':run,'capture':data['state']['summary'],'sensors':{},'delays_assumed_in_measurement':False}
private={}
for model,text in data['logs'].items():
    pairs={int(r):(int(s),float(m)) for s,r,m in re.findall(r'Pair epoch=1 sof=(\d+) request=(\d+) population=\d+ mean=([\d.e+-]+)',text)}
    domains={'BHIST':{s:m for s,m in pairs.values()}}
    for i in range(4):
        domains['Y'+str(i)]={pairs[int(r)][0]:list(map(float,values.split()))[i] for r,values in re.findall(r'APPLICATION_LUMA request=(\d+)((?: [\d.e+-]+){4})',text) if int(r) in pairs}
    events=[(int(s),int(p),int(t),int(o)) for s,p,t,o in re.findall(r'STEPPER_SOF sequence=(\d+) pending=(\d+) event_ns=(\d+) observed_ns=(\d+)',text)]
    writes=[dict(step=int(step),sof=int(sof),control='exposure' if int(cid)==0x980911 else 'analogue_gain',value=int(value),
                 event_ns=int(t),begin_ns=int(b),end_ns=int(e),ret=int(ret)) for step,sof,cid,value,t,b,e,ret in re.findall(
        r'CONTROL_WRITE step=(\d+) sof=(\d+) id=(\d+) value=(\d+) event_ns=(\d+) begin_ns=(\d+) end_ns=(\d+) ret=(-?\d+) errno=\d+',text)]
    steps=[];privateSteps=[]
    for w in writes:
        n=w['sof'];results={};rawResults={}
        for domain,means in domains.items():
            pre=[means[s] for s in range(n-6,n) if s in means];post=[means[s] for s in range(n+6,n+14) if s in means]
            if len(pre)!=6 or len(post)!=8 or any(n+k not in means for k in range(8)):
                results[domain]={'usable':False,'reason':'missing paired samples'};continue
            a,b=statistics.median(pre),statistics.median(post);delta=b-a
            noise=max(statistics.median(abs(v-a) for v in pre),statistics.median(abs(v-b) for v in post),1e-6)
            usable=abs(delta)>10*noise and abs(delta)>max(abs(a),abs(b))*.05
            response=[(means[n+k]-a)/delta if delta else 0 for k in range(8)]
            first=next((k for k in range(6) if all(.15<=v<=1.5 for v in response[k:k+3])),None) if usable else None
            plateau=next((k for k in range(6) if all(.85<=v<=1.15 for v in response[k:k+3])),None) if usable else None
            results[domain]={'usable':usable,'first_changed_offset':first,'three_frame_plateau_offset':plateau}
            rawResults[domain]={'pre':a,'post':b,'noise':noise,'response':response}
        public={k:v for k,v in w.items() if k not in ['event_ns','begin_ns','end_ns']}
        public.update(write_start_after_sof_us=round((w['begin_ns']-w['event_ns'])/1000,3),
                      write_duration_us=round((w['end_ns']-w['begin_ns'])/1000,3),domains=results)
        steps.append(public);privateSteps.append({'write':w,'domains':rawResults})
    delays={}
    for control in ['exposure','analogue_gain']:
        useful=[d for s in steps if s['control']==control for d in s['domains'].values() if d['usable']]
        delays[control]={'usable_domains':len(useful),'first_changed_offsets':sorted(set(d['first_changed_offset'] for d in useful),key=str),
                         'plateau_offsets':sorted(set(d['three_frame_plateau_offset'] for d in useful),key=str)}
    report['sensors'][model]={'paired_images':len(pairs),'observed_sofs':len(events),
        'sof_continuity':bool(events) and [e[0] for e in events]==list(range(events[-1][0]+1)),
        'event_pending':max((e[1] for e in events),default=-1),
        'frame_period_us':round(statistics.median((b[2]-a[2])/1000 for a,b in zip(events,events[1:])),3) if len(events)>1 else None,
        'steps':steps,'observed_delays':delays,'sensor_model_scope_only':True}
    private[model]=privateSteps
report['capture_passed']=report['capture']['passed']
(host.PRIVATE/('delay-'+run+'-analysis.json')).write_text(json.dumps(private,indent=2)+'\n')
(HERE/('delay-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'capture_passed':report['capture_passed'],'sensors':{m:{k:v for k,v in s.items() if k!='steps'} for m,s in report['sensors'].items()}},indent=2))
