"""Independently relate control writes to paired linear ISP statistics, privately."""
from pathlib import Path
import hashlib,json,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run)
poll=json.loads((P/f'delay-{run}-poll-private.json').read_text());assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live']
summary=poll['summary'];assert summary['passed']
root='/var/lib/samurai/k301-delay-'+run
raw=host.ssh('cat '+shlex.quote(root+'/capture-private.log'),timeout=20).stdout
(P/f'delay-{run}-capture-private.log').write_bytes(raw);text=raw.decode(errors='replace')
pairs=[(int(e),int(s),int(r),int(p),float(m),int(a)) for e,s,r,p,m,a in re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',text)]
assert len(pairs)==summary['application_frames'] and len({s for _,s,_,_,_,_ in pairs})==len(pairs)
assert all(e==1 and a==1 and p>0 for e,_,_,p,_,a in pairs)
means={s:m for _,s,_,_,m,_ in pairs};events=summary['sof_events'];assert [e['sof'] for e in events]==list(range(233))
periods=[b['event_ns']-a['event_ns'] for a,b in zip(events,events[1:])];period=statistics.median(periods)
results=[]
for w in summary['control_writes']:
 n=w['sof'];before=[means[x] for x in range(n-6,n)];after=[means[x] for x in range(n+6,n+14)]
 pre=statistics.median(before);post=statistics.median(after);delta=post-pre
 mad=lambda values,median:statistics.median(abs(v-median) for v in values)
 noise=max(mad(before,pre),mad(after,post),.000001)
 usable=abs(delta)>10*noise and abs(delta)>max(abs(pre),abs(post))*.05
 response=[(means[n+k]-pre)/delta if delta else None for k in range(8)]
 first=next((k for k in range(6) if all(.15<=r<=1.5 for r in response[k:k+3])),None) if usable else None
 settled=next((k for k in range(6) if all(.85<=r<=1.15 for r in response[k:k+3])),None) if usable else None
 results.append(dict(step=w['step'],sof=n,control='exposure' if w['id']==0x980911 else 'analogue_gain',value=w['value'],
  pre_median=pre,post_median=post,robust_noise=noise,normalized_response=response,
  write_start_after_sof_us=(w['begin_ns']-w['event_ns'])/1000,write_duration_us=(w['end_ns']-w['begin_ns'])/1000,
  useful_response=usable,first_observed_changed_offset=first,first_three_frame_plateau_offset=settled))
private=dict(run=run,statistics_domain='empirical post-BLS/pre-WB linear Y BHIST',frame_period_ns=period,changes=results)
(P/f'delay-{run}-analysis-private.json').write_text(json.dumps(private,indent=2)+'\n')
bundle=json.loads((HERE/'delay-bundle-validation.json').read_text())
code='from pathlib import Path;import hashlib,json;p=Path('+repr(root+'/bundle')+');print(json.dumps({n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in '+repr(list(bundle['files']))+'}))'
readback=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert readback=={n:r['sha256'] for n,r in bundle['files'].items()}
public=dict(stage=301,run=run,actual_kernel_build=298,paired_images=len(pairs),observed_sofs=len(events),control_steps=len(results),
 all_nine_phone_bundle_hashes_match=True,frame_period_us=round(period/1000,3),
 steps=[{k:v for k,v in r.items() if k not in ['pre_median','post_median','robust_noise','normalized_response']} for r in results],
 no_scene_or_unit_calibration_values_published=True,not_dark_calibration=True,
 statistics_response_does_not_prove_full_frame_pixel_or_embedded_register_latching=True,
 no_delay_properties_committed=True,ae_or_awb_not_implemented=True)
(HERE/f'delay-analysis-{run}-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public,indent=2))
