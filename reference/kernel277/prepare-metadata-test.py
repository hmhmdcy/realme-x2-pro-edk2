"""Use fresh outputs for a real r23 metadata-versus-RAW comparison."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'test-raw-focus.py').read_text()
for a,b in [('focus-probe-build-validation.json','metadata-probe-build-validation.json'),('focus-raw277','focus-metadata277'),
 ('raw-focus-r1','focus-metadata-r1'),('candidate_helper_only=True','candidate_helper_only=False'),
 ('system_libcamera_still_r22=True',"framework_version='99990.7.2-r23'"),('focus_fom_metadata_not_deployed=True','focus_fom_metadata_not_deployed=False')]:s=s.replace(a,b)
anchor="  accepted=frames[12:];assert all(abs(f['exposure_us']-32000)<=40 and abs(f['analogue_gain']-1)<.03 for f in accepted)"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n  matched=[f for f in accepted if f['metadata_focus_fom'] is not None];assert len(matched)>=3\n  assert all(f['metadata_focus_fom'] is None or f['metadata_focus_fom']==f['focus_fom'] for f in frames),'Focus metadata does not match the RAW of this request'")
anchor="  public.append(row);runs.append(data);"
assert s.count(anchor)==1;s=s.replace(anchor,"  row.update(metadata_focus_samples=len(matched),metadata_matches_same_request_raw=True)\n"+anchor)
compile(s,'test-focus-metadata.py','exec');p=R/'test-focus-metadata.py';assert not p.exists();p.write_text(s)
print('Fresh native metadata identity test prepared')
