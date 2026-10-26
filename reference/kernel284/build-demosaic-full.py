"""Run the same guarded Kbuild workflow for the committed Demosaic36 candidate."""
from pathlib import Path

path=Path(__file__).resolve().with_name('build-wb-full.py')
source=path.read_text()
changes=[
    ("COMMIT='97a4c563803fd943e5a4c3f0359548a3d758bcc5'", "COMMIT='af9e2a02365a2ec1a19d3cc42da5c65e84c244c4'"),
    ("assert git('rev-parse','HEAD')==BASE and not git('status','--porcelain')", "assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')"),
]
for old,new in changes:
    assert source.count(old)==1
    source=source.replace(old,new)
source=source.replace('samurai-vfe175-wb283','samurai-vfe175-demosaic284')
source=source.replace('wb-','demosaic-')
exec(compile(source,str(path),'exec'),globals())
