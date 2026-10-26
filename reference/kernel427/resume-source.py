"""Finish the known partial authoring transaction after whitespace matching failed."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354';directory=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
base='dbefc5bdd8de8da07128171423f098a38d6e45b0';assert git('rev-parse','HEAD').strip()==base and git('branch','--show-current').strip()=='samurai-vfe175-ds4-dma427'
changed=[Path(p) for p in git('diff','--name-only').splitlines()];assert len(changed)==11
assert (kernel/directory/'camss-vfe.c').read_bytes()==git('show',base+':'+str(directory/'camss-vfe.c')).encode()
def read(name):return (kernel/directory/name).read_text()
def write(name,text):
 path=directory/name;(kernel/path).write_text(text);changed.append(path)
def replace(text,old,new,count=1):
 assert text.count(old)==count,(old,text.count(old),count);return text.replace(old,new)
source=(HERE/'prepare-kernel.py').read_text();tail=source[source.index("text=read('camss-vfe.c');"):]
exec(compile(tail,'resume-camss-vfe-authoring','exec'))
