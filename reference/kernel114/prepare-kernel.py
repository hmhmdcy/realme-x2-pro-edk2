from pathlib import Path
import subprocess, json

stage=Path('/home/cy122/pmos-samurai-kernel114')
before=Path('/home/cy122/pmos-samurai-kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel114')
assert not stage.exists()
stage.mkdir()
for name in ['kernel','initramfs']:
    subprocess.run(['cp','-a','--reflink=auto',str(before/name),str(stage/name)],check=True)
kernel=stage/'kernel'
config=kernel/'.config'
config.write_text(config.read_text().replace(str(before/'initramfs'),str(stage/'initramfs')))
subprocess.run(['scripts/config','--enable','ZSMALLOC','--module','ZRAM','--enable','SYN_COOKIES'],cwd=kernel,check=True)
sources=out/'primary-reference/aports/device/testing/linux-oneplus-hotdog-mainline616'
plans=[]
for p in sorted(sources.glob('014[45]-*.patch')):
    result=subprocess.run(['git','apply','--check',str(p)],cwd=kernel,capture_output=True,text=True)
    plans.append(dict(name=p.name,clean_apply=result.returncode==0,diagnostic=result.stderr))
(out/'ipa-patch-plan.json').write_text(json.dumps(plans,indent=2)+'\n')
print(json.dumps(plans,indent=2))
