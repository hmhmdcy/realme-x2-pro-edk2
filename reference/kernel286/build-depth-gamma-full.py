"""Run the guarded normal Kbuild workflow for the final 286 commit."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
previous=ROOT.parent/'kernel285/build-cst-full.py'
s=previous.read_text()
changes=[
    ('/mnt/e/edk2-samurai-out/kernel285','/mnt/e/edk2-samurai-out/kernel286'),
    ("COMMIT='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'","COMMIT='209d1ea0f0a53e9a725ad288c159baddbc83aef7'"),
    ("ROOT.parent/'kernel284/demosaic-full-build-validation.json'","ROOT.parent/'kernel285/cst-full-build-validation.json'"),
    ('completed-demosaic284','completed-cst285'),
    ("'cst-","'depth-gamma-"),
    ("KBUILD_BUILD_VERSION='285'","KBUILD_BUILD_VERSION='286'"),
    ('stage=285','stage=286')]
for before,after in changes:
    assert before in s,before;s=s.replace(before,after)
needle="assert any(n.endswith('/camss-vfe-175-cst.o') for n in components)"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n    assert len(components)==37 and all(any(n.endswith('/'+name) for n in components) for name in ['camss-vfe-175-round.o','camss-vfe-175-gamma.o'])")
exec(compile(s,str(previous),'exec'),globals())
