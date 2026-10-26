"""Prepare new complete-package QA entry points without reusing old output directories."""
from pathlib import Path
R=Path(__file__).resolve().parent
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-runtime-repo.py','qa-packages.py']:
 source=(R.parent/'kernel273'/name).read_text()
 for a,b in [('kernel273','kernel275'),('273-r21','275-r22'),('r21','r22'),('stage=273','stage=275'),('k273','k275'),('0.1.0-r16','0.1.0-r17')]:source=source.replace(a,b)
 compile(source,name,'exec');p=R/name;assert not p.exists();p.write_text(source)
print('275 complete-package QA entry points prepared')
