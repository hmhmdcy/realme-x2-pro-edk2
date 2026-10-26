"""Build both committed fixes with the deployed kernel288 boot configuration."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
previous=ROOT.parent/'kernel285/build-cst-full.py'
s=previous.read_text()
for a,b in [
 ('/mnt/e/edk2-samurai-out/kernel285','/mnt/e/edk2-samurai-out/kernel289'),
 ("COMMIT='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'","COMMIT='ff8d2e9fc04ef92407ff83c40c4e059eb620f0f7'"),
 ('0c26bd9147ac31b92d824b8dbd529384772be3c8ae819314240cdd6cbde3a6ca','34204656424a03b7904c6d079aa0b112dafcec220b2a27b23c7b9afaa4eca8b2'),
 ("ROOT.parent/'kernel284/demosaic-full-build-validation.json'","ROOT.parent/'kernel288/boot-candidate-build-validation.json'"),
 ('completed-demosaic284','completed-boot288'),("'cst-","'fixes-"),
 ("KBUILD_BUILD_VERSION='285'","KBUILD_BUILD_VERSION='289'"),('stage=285','stage=289')]:
 assert a in s,a;s=s.replace(a,b)
needle="assert any(n.endswith('/camss-vfe-175-cst.o') for n in components)"
s=s.replace(needle,needle+'\n    assert len(components)==39')
exec(compile(s,str(previous),'exec'),globals())
