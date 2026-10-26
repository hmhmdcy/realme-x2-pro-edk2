"""Create isolated full-feature r23 QA entry points."""
from pathlib import Path
R=Path(__file__).resolve().parent
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-runtime-repo.py','qa-packages.py']:
 s=(R.parent/'kernel275'/name).read_text()
 for a,b in [('kernel275','kernel277'),('275-r22','277-r23'),('r22','r23'),('stage=275','stage=277'),('k275','k277'),('0.1.0-r17','0.1.0-r18')]:s=s.replace(a,b)
 compile(s,name,'exec');p=R/name;assert not p.exists();p.write_text(s)
print('Isolated r23 full-feature QA prepared')
