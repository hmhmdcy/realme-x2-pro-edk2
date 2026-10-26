"""Build the committed PIX candidate on the verified existing E-drive build volume."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
previous=ROOT.parent/'kernel285/build-cst-full.py'
s=previous.read_text()
for before,after in [
    ('/mnt/e/edk2-samurai-out/kernel285','/mnt/e/edk2-samurai-out/kernel288'),
    ("COMMIT='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'","COMMIT='8c79b7e1912790d3e18a84c9c6621a6d92baa768'"),
    ("ROOT.parent/'kernel284/demosaic-full-build-validation.json'","ROOT.parent/'kernel287/demux-mnds-full-build-validation.json'"),
    ('completed-demosaic284','completed-demux-mnds287'),
    ("'cst-","'pix-"),("KBUILD_BUILD_VERSION='285'","KBUILD_BUILD_VERSION='288'"),('stage=285','stage=288')]:
    assert before in s,before;s=s.replace(before,after)
needle="assert any(n.endswith('/camss-vfe-175-cst.o') for n in components)"
assert needle in s;s=s.replace(needle,needle+'\n    assert len(components)==39')
exec(compile(s,str(previous),'exec'),globals())
