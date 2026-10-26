"""Prepare the actual-k295 guarded investigation without a phone mutation."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel295'
s='''from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('camera295_transport',Path(__file__).resolve().parents[1]/'kernel295/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel296');PRIVATE.mkdir(mode=0o700,exist_ok=True)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
'''
p=ROOT/'host.py';assert not p.exists();p.write_text(s)
s=(ROOT.parent/'kernel294/inspect-current.py').read_text().replace('k293','k295').replace("'#293 '","'#295 '").replace('stage=294','stage=296').replace('kernel_build=293','kernel_build=295')
p=ROOT/'inspect-current.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared strict current-k295 read-only inspection.')
