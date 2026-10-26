"""Inspect the authoritative kernel and retained original GTM transport."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage433inspect',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);build=m.mounted_build();kernel=build.parent/'source354'
git=lambda where,*a:subprocess.check_output(['git','-C',str(where),*a],text=True).strip()
assert git(kernel,'rev-parse','HEAD')=='52127e558704de6a640d076ef605182fe6fff0d7' and not git(kernel,'status','--porcelain')
repo=Path('/home/cy122/edk2-samurai/repo');assert git(repo,'rev-parse','HEAD')=='cb32e82c0ffd94456b9d092c3eaf76650217f00c'
directory=kernel/'drivers/media/platform/qcom/camss';names=[p.name for p in directory.glob('*') if any(word in p.name for word in ['param','colour','175','stats'])]
print(json.dumps(dict(kernel_commit=git(kernel,'rev-parse','HEAD'),mirror_commit=git(repo,'rev-parse','HEAD'),files=names)))
out=P/'kernel-before';out.mkdir(exist_ok=True)
for name in names:
 source=directory/name
 if source.is_file():(out/name).write_bytes(source.read_bytes())
for tag,entry,size in [('gtm-create',0x31f7f0,0x23c),('gtm-initialize',0x31fa30,0x1cc),('packet-write-dmi',0x52d2e8,0x500)]:
 (P/(tag+'-private.asm')).write_bytes(subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(entry),'--stop-address='+hex(entry+size),str(P.parent/'kernel281/camera.qcom.so-private')]))
