"""Derive the bounded tested harness into fresh 264 contexts."""
from pathlib import Path
import re
R=Path(__file__).parent;old=R.parent/'kernel263'
for name in ['baseline.py','advanced-probe.py','select-front.py','pipewire263.conf','wireplumber263-off.conf']:
 s=(old/name).read_text().replace('k263','k264').replace('K263','K264').replace('samurai263','samurai264').replace('stage=263','stage=264')
 if name=='advanced-probe.py':
  needle="data['pts_span_seconds']=(pts[-1]-pts[0])/Gst.SECOND if len(pts)>1 else 0"
  assert s.count(needle)==1
  s=s.replace(needle,needle+"\ndata['pts_max_gap_seconds']=max((b-a)/Gst.SECOND for a,b in zip(pts,pts[1:])) if len(pts)>1 else 0\ndata['pts_regressions']=[dict(index=i+1,before=a,after=b) for i,(a,b) in enumerate(zip(pts,pts[1:])) if b<=a]")
 target=name.replace('263','264');(R/target).write_text(s)
s=(old/'advanced-runner.py').read_text().replace('k263','k264').replace('K263','K264').replace('samurai263','samurai264').replace('pipewire263','pipewire264').replace('wireplumber263','wireplumber264')
start=s.index('mode=int(');end=s.index("root=Path(",start)
s=s[:start]+"mode=int(sys.argv[1]);assert mode in range(6000041,6000053)\nscenario={6000041:6000017,6000042:6000018,6000043:6000014,6000044:6000019,6000045:6000016,6000046:6000015,6000047:6000017,6000048:6000018,6000049:6000014,6000050:6000019,6000051:6000016,6000052:6000015}[mode]\nbroadcast=True\n"+s[end:]
(R/'advanced-runner.py').write_text(s)
s=(old/'native-advanced.py').read_text().replace('k263','k264').replace('stage=263','stage=264')
s=re.sub(r"which,kind='front','rgb';delay=int\(sys.argv\[1\]\);assert delay in [^\n]+", "which,kind='front','rgb';delay=int(sys.argv[1]);assert delay in range(6000041,6000053)",s,count=1)
(R/'native-advanced.py').write_text(s)
