"""Independent effective-control, IPC provenance and physical AE checks."""
from pathlib import Path
import hashlib, json, math, re, shlex, statistics, sys
import host
HERE = Path(__file__).resolve().parent
run = sys.argv[1]
assert re.fullmatch(r'r[1-9][0-9]*', run)
poll = json.loads((host.PRIVATE/f'ae-{run}-poll-private.json').read_text())
assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live'] and poll['summary']['passed']
root = '/var/lib/samurai/k306-ae-'+run
raw = host.ssh('cat '+shlex.quote(root+'/capture-private.log'), timeout=20).stdout
(host.PRIVATE/f'ae-{run}-capture-private.log').write_bytes(raw)
text = raw.decode(errors='replace')
contexts = {(int(e),int(s)):(int(v),int(x),int(g),int(c)) for e,s,v,x,g,c in
 re.findall(r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)',text)}
metadata = {(int(e)+1,int(r)):(int(x),float(g),int(em),int(gm)) for e,r,x,g,em,gm in
 re.findall(r'APPLICATION_SENSOR_METADATA epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+) exposure_mode=(\d+) gain_mode=(\d+)',text)}
pairs = [(int(e),int(s),int(r),int(p),float(m),int(a)) for e,s,r,p,m,a in
 re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',text)]
updates = {(int(e),int(v)):(int(s),int(x),int(g)) for e,s,v,x,g in
 re.findall(r'AE update epoch=(\d+) stats-sof=(\d+) revision=(\d+) exposure-lines=(\d+) gain-code=(\d+)',text)}
luma = {(int(e)+1,int(r)):list(map(float,(a,b,c,d))) for e,r,a,b,c,d in
 re.findall(r'APPLICATION_LUMA epoch=(\d+) request=(\d+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+)',text)}
assert len(pairs)==len(metadata)==480 and len({(e,s) for e,s,*_ in pairs})==480
lineUs = 9648*1000000/481930000
rounded = lambda n:math.floor(n+.5)
means, actual, first, pixels = {}, {}, {}, {}
for e,s,r,p,m,a in pairs:
    v,x,g,c = contexts[e,s]; assert v and p==820560 and a==1
    assert 1<=x<=1659 and 32<=g<=512
    wanted = metadata[e,r]
    expectedGain=g/32
    # The fixture prints floats with six significant digits.
    assert wanted[0]==rounded(x*lineUs) and abs(wanted[1]-expectedGain)<=5e-6*max(1,expectedGain) and wanted[2:]==(0,0), (e,s,r,(x,g,c),wanted,rounded(x*lineUs),expectedGain)
    if c!=0xffffffff:
        origin,px,pg=updates[e,c];assert (x,g)==(px,pg)
        first.setdefault((e,c),s);assert s>=origin+2
    actual[e,s]=(x,g,c);means[e,s]=m/1024;pixels[e,s]=luma[e,r]
trace=[];current=None
for row in text.splitlines():
    m=re.search(r'SOF epoch=(\d+) sequence=(\d+)',row)
    if m:current=(int(m[1]),int(m[2]))
    m=re.search(r'DelayedControls .*Setting (Exposure|Analogue Gain) to (\d+) at index',row)
    if m:assert current;trace.append((*current,m[1],int(m[2])))
expected=[]
for (e,c),s in first.items():
    new=actual[e,s]
    # Every automatic proposal submits both controls, including an unchanged member.
    expected.append((e,s-2,'Exposure',new[0]))
    expected.append((e,s-2,'Analogue Gain',new[1]))
assert all(row in trace for row in expected)
last={e:max(s for ep,s in actual if ep==e) for e in [1,2]}
unexpected=[row for row in trace if row not in expected and row[1]+2<=last[row[0]]]
assert not unexpected, (len(trace),len(expected),unexpected[:12])
physical=[]
for (e,c),s in first.items():
    if s<3 or s+2>239:continue
    old,new=actual[e,s-1],actual[e,s]
    evRatio=(new[0]*new[1])/(old[0]*old[1])
    measured=[]
    for domain in range(5):
        curve={k:(means[e,k] if domain==0 else pixels[e,k][domain-1]) for k in range(s-3,s+3)}
        before=[curve[k] for k in range(s-3,s)];after=[curve[k] for k in range(s,s+3)]
        pre,post=statistics.median(before),statistics.median(after);delta=post-pre
        noise=max(statistics.median(abs(v-pre) for v in before),statistics.median(abs(v-post) for v in after),1e-7)
        useful=abs(delta)>6*noise and abs(delta)>.005*max(abs(pre),abs(post),1e-7)
        sameDirection=(evRatio-1)*delta>0
        aligned=useful and sameDirection and abs(curve[s-1]-pre)<.15*abs(delta) and all((curve[k]-pre)/delta>=.15 for k in range(s,s+3))
        measured.append(dict(useful=useful,response_direction_matches_ev=sameDirection,first_response_aligned=aligned))
    physical.append(dict(epoch=e,revision=c,effective_sof=s,domains=measured))
results=[]
for e in [1,2]:
    curve=[means[e,s] for s in range(240)]
    tail=curve[-40:];median=statistics.median(tail)
    settled=all(abs(v-.16)<.01 for v in tail)
    bound=all(actual[e,s][0]>=1657 and actual[e,s][1]==512 for s in range(200,240))
    bound=bound and max(tail)-min(tail)<.01 and median<.16
    convergence=next((s for s in range(221) if all(abs(v-.16)<.01 for v in curve[s:s+20])),None)
    results.append(dict(epoch=e,frames=240,final40_within_target_tolerance=settled,
                        twenty_consecutive_frames_within_target_first_sof=convergence,
                        stable_at_sensor_upper_limits_below_target=bound,
                        effective_revisions=sum(ep==e for ep,c in first),
                        maximum_final_relative_target_error=round(max(abs(v-.16) for v in tail),6)))
    (host.PRIVATE/f'ae-{run}-epoch{e}-luminance-private.json').write_text(json.dumps(dict(first=curve[0],tail_median=median,minimum=min(curve),maximum=max(curve)))+'\n')
receipt=HERE/f'ae-{run}-bundle-validation.json'
bundle = json.loads((receipt if receipt.exists() else HERE/'bundle-ae-validation.json').read_text())
code='from pathlib import Path;import hashlib,json;p=Path('+repr(root+'/bundle')+');print(json.dumps({n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in '+repr(list(bundle['files']))+'}))'
hashes=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert hashes=={n:item['sha256'] for n,item in bundle['files'].items()}
report=dict(stage=306,run=run,actual_kernel_build=298,frames=480,standard_auto_mode_metadata_frames=480,
            proposal_count=len(updates),effective_revisions=len(first),real_writes_verified=len(expected),
            all_completed_writes_effective_at_sof_plus2=True,exact_request_sof_context_metadata_verified=True,
            gain_text_relative_tolerance=5e-6,
            physical_control_steps=physical,
            useful_physical_domains=sum(d['useful'] for c in physical for d in c['domains']),
            aligned_physical_domains=sum(d['first_response_aligned'] for c in physical for d in c['domains']),
            phone_bundle_hashes_verified=True,isolated_ipc=bool(poll['summary']['ipa_isolation_requested']),
            proposal_to_effective_offsets=sorted(set(s-updates[e,c][0] for (e,c),s in first.items())),
            epochs=results,target_tolerance=.01,all_epochs_reached_target=all(r['final40_within_target_tolerance'] for r in results),
            passed=all(r['final40_within_target_tolerance'] or r['stable_at_sensor_upper_limits_below_target'] for r in results),
            full_iq_calibration=False,awb_implemented=False)
(HERE/f'ae-{run}-association-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='physical_control_steps'},indent=2))
