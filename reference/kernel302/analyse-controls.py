"""Independent request/source/SOF/metadata and physical response cross-check."""
from pathlib import Path
import hashlib,json,math,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run)
poll=json.loads((P/f'controls-{run}-poll-private.json').read_text());assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live']
summary=poll['summary'];assert summary['passed']
root='/var/lib/samurai/k302-controls-'+run
raw=host.ssh('cat '+shlex.quote(root+'/capture-private.log'),timeout=20).stdout
(P/f'controls-{run}-capture-private.log').write_bytes(raw);text=raw.decode(errors='replace')
contexts={(int(e),int(s)):(int(v),int(x),int(g),int(c)) for e,s,v,x,g,c in re.findall(r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)',text)}
metadata={(int(e)+1,int(r)):(int(x),float(g)) for e,r,x,g in re.findall(r'APPLICATION_SENSOR_METADATA epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)}
luma={(int(e)+1,int(r)):[float(a),float(b),float(c),float(d)] for e,r,a,b,c,d in re.findall(r'APPLICATION_LUMA epoch=(\d+) request=(\d+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+)',text)}
commands=[(int(e)+1,int(r),int(x),float(g)) for e,r,x,g in re.findall(r'APPLICATION_SENSOR_COMMAND epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)]
pairs=[(int(e),int(s),int(r),int(p),float(m),int(a)) for e,s,r,p,m,a in re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',text)]
assert len(pairs)==len(metadata)==len(luma)==480 and len(commands)==18
mode_metadata=re.findall(r'APPLICATION_SENSOR_METADATA epoch=\d+ request=\d+ exposure_us=\d+ analogue_gain=[\d.e+-]+ exposure_mode=(\d+) gain_mode=(\d+)',text)
if mode_metadata:assert len(mode_metadata)==480 and all(x==g=='1' for x,g in mode_metadata)
assert len({(e,s) for e,s,_,_,_,_ in pairs})==len(pairs) and len({(e,r) for e,_,r,_,_,_ in pairs})==len(pairs)
line=2080*1000000/209066666
rounded=lambda n:math.floor(n+.5)
source={};initial=0xffffffff
for epoch in [1,2]:
 state=[503,512];source[epoch,initial]=tuple(state)
 for e,r,x,g in commands:
  if e!=epoch:continue
  if x:state[0]=rounded(x/line)
  if g:state[1]=rounded(1024-1024/g)
  source[e,r]=tuple(state)
means={};bands={};paired_contexts={}
for e,s,r,p,m,a in pairs:
 v,x,g,c=contexts[e,s];assert v and p==499392 and a==1 and (x,g)==source[e,c]
 actual=metadata[e,r];assert actual[0]==rounded(x*line) and abs(actual[1]-1024/(1024-g))<.00001
 means[e,s]=m;bands[e,s]=luma[e,r];paired_contexts[e,s]=(x,g,c)
results=[]
def response(values,n):
 before=[values[k] for k in range(n-6,n-2)];after=[values[k] for k in range(n+6,n+14)]
 pre=statistics.median(before);post=statistics.median(after);delta=post-pre
 mad=lambda a,m:statistics.median(abs(v-m) for v in a)
 noise=max(mad(before,pre),mad(after,post),.000001)
 usable=abs(delta)>10*noise and abs(delta)>max(abs(pre),abs(post))*.03
 curve={k:(values[n+k]-pre)/delta if delta else 0 for k in range(-2,8)}
 first=next((k for k in range(-2,6) if all(.15<=curve[j]<=1.5 for j in range(k,k+3))),None) if usable else None
 plateau=next((k for k in range(-2,6) if all(.85<=curve[j]<=1.15 for j in range(k,k+3))),None) if usable else None
 return dict(useful=usable,first_changed_offset=first,three_frame_plateau_offset=plateau,private_pre=pre,private_post=post,private_curve=curve)
for e in [1,2]:
 for n in range(1,240):
  if paired_contexts[e,n][2]==paired_contexts[e,n-1][2]:continue
  r=paired_contexts[e,n][2]
  domains=[response({s:y for (epoch,s),y in means.items() if epoch==e},n)]
  domains += [response({s:y[b] for (epoch,s),y in bands.items() if epoch==e},n) for b in range(4)]
  results.append(dict(epoch=e,source_request=r,effective_sof=n,domains=domains))
assert len(results)==18
write_trace=[];current=None
for line_text in text.splitlines():
 m=re.search(r'SOF epoch=(\d+) sequence=(\d+)',line_text)
 if m:current=(int(m[1]),int(m[2]))
 m=re.search(r'DelayedControls .*Setting (.+?) to (\d+) at index (\d+)',line_text)
 if m:
  assert current is not None and m[1] in ['Exposure','Analogue Gain']
  write_trace.append((*current,'exposure' if m[1]=='Exposure' else 'gain',int(m[2])))
write_proof=False
if write_trace:
 expected=[]
 for item in results:
  e,n=item['epoch'],item['effective_sof'];old=paired_contexts[e,n-1];new=paired_contexts[e,n]
  if old[0]!=new[0]:expected.append((e,n-2,'exposure',new[0]))
  if old[1]!=new[1]:expected.append((e,n-2,'gain',new[1]))
 assert len(write_trace)==18 and write_trace==expected
 write_proof=True
private=dict(run=run,changes=results)
(P/f'controls-{run}-association-private.json').write_text(json.dumps(private,indent=2)+'\n')
bundle_run=sys.argv[2] if len(sys.argv)>2 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',bundle_run)
bundle=json.loads((HERE/f'ipa-bundle-{bundle_run}-validation.json').read_text())
code='from pathlib import Path;import hashlib,json;p=Path('+repr(root+'/bundle')+');print(json.dumps({n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in '+repr(list(bundle['files']))+'}))'
hashes=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout);assert hashes=={n:i['sha256'] for n,i in bundle['files'].items()}
public=dict(stage=302,run=run,actual_kernel_build=298,archive_sha256=bundle['archive_sha256'],module_sha256=bundle['files']['ipa/ipa_camss_vfe.so']['sha256'],independent_request_source_sof_quantized_metadata_crosscheck=True,frames=480,source_control_changes=len(results),all8_phone_bundle_hashes_match=True,
 delayed_control_write_sof_verified=write_proof,all_logged_writes_effective_at_sof_plus2=write_proof,standard_manual_mode_metadata_frames=len(mode_metadata),
 request_to_effective_sof_offsets=sorted(set(r['effective_sof']-r['source_request'] for r in results)),
 changes=[dict(epoch=r['epoch'],source_request=r['source_request'],effective_sof=r['effective_sof'],
  domains=[{k:v for k,v in d.items() if not k.startswith('private_')} for d in r['domains']]) for r in results],
 domains_in_order=['post_BLS_pre_WB_linear_BHIST','NV12_luma_top_quarter','NV12_luma_second_quarter','NV12_luma_third_quarter','NV12_luma_bottom_quarter'],
 scene_measurements_kept_private=True,not_dark_or_full_iq_calibration=True)
public['all_bhist_changes_align_with_effective_metadata']=all(r['domains'][0]['useful'] and r['domains'][0]['first_changed_offset']==r['domains'][0]['three_frame_plateau_offset']==0 for r in results)
public['all_useful_output_bands_align_with_effective_metadata']=all(d['first_changed_offset']==d['three_frame_plateau_offset']==0 for r in results for d in r['domains'][1:] if d['useful'])
public['useful_output_band_changes']=sum(d['useful'] for r in results for d in r['domains'][1:])
(HERE/f'control-association-{run}-validation.json').write_text(json.dumps(public,indent=2)+'\n')
print(json.dumps({k:v for k,v in public.items() if k!='changes'},indent=2))
