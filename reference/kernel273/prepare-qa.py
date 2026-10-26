"""Create new QA entrypoints; no old output directory or transaction is reused."""
from pathlib import Path
R=Path(__file__).resolve().parent
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-runtime-repo.py']:
 source=(R.parent/'kernel271'/name).read_text()
 for a,b in [('kernel271','kernel273'),('271-r20','273-r21'),('r20','r21'),('stage=271','stage=273'),('k271','k273'),('0.1.0-r15','0.1.0-r16')]:source=source.replace(a,b)
 compile(source,name,'exec');p=R/name;assert not p.exists();p.write_text(source)
print('273 QA entrypoints prepared')
