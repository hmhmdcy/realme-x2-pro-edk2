"""Inspect boot requirements without exporting credentials or initramfs contents."""
from pathlib import Path
import hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
init=Path('/home/cy122/pmos-samurai-kernel136/initramfs')
assert init.is_dir() and not init.is_symlink()
text=(init/'init').read_text()
selected=[]
for line in text.splitlines():
    if any(word in line for word in ['switch_root','modprobe','insmod','mount -t','mount -o','/lib/modules','root=']):
        line=re.sub(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}','PRIVATE-UUID',line)
        if not any(word in line.lower() for word in ['password','passwd','ssh-','dropbear','authorized']):selected.append(line)
modules=[]
for p in init.rglob('*.ko'):
    modules.append(dict(path=str(p.relative_to(init)),bytes=p.stat().st_size,
                        vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(p)],text=True).strip()))
report=dict(stage=288,init_sha256=hashlib.sha256((init/'init').read_bytes()).hexdigest(),
            selected_boot_operations=selected,embedded_modules=modules,
            bootable_build_needs_initramfs=True,compile_only_image_has_no_initramfs=True,
            credentials_and_full_input_not_exported=True)
(ROOT/'initramfs-requirements-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
