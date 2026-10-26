"""Use retained physical captures to check the statistics tap around GTM."""
from pathlib import Path
import hashlib,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P.parent/'kernel434/runtime-collected-r2/pattern'
groups={1:set(),2:set()};count=0
for p in root.glob('stats-*.bin'):
 raw=p.read_bytes();version,size=struct.unpack_from('<II',raw);assert version==1 and size+8==len(raw);at=8;seen=set()
 while at<len(raw):
  kind,flags,n=struct.unpack_from('<HHI',raw,at);assert n>=8 and n%8==0 and not flags and at+n<=len(raw)
  if kind in groups:groups[kind].add(hashlib.sha256(raw[at:at+n]).hexdigest());seen.add(kind)
  at+=n
 assert seen=={1,2};count+=1
assert count==61 and len(groups[1])==len(groups[2])==1
r=dict(stage=435,retained_physical_capture_stage=434,pattern_frames=count,gtm_phases=9,bhist_distinct_payloads=len(groups[1]),bg_distinct_payloads=len(groups[2]),bhist_and_bg_invariant_while_gtm_changes_full_and_pd10=True,scope='Existing selected IFE statistics tap with fixed test-pattern input and fixed WB; supports pre-GTM statistics interpretation, not a register readback or proof of every tap/mode',no_new_phone_experiment=True,passed=True)
(HERE/'statistics-domain-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
