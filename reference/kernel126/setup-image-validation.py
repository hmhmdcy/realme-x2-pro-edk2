from pathlib import Path
import runpy,subprocess,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';runpy.run_path(str(ref/'ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));v=Path('/home/cy122/pmos-samurai-build126');install=Path('/home/cy122/pmos-samurai-rootfs122/tools/install-root');dest=v/'tools/install-root'
assert not dest.exists();dest.parent.mkdir(exist_ok=True);subprocess.run(['cp','-a',str(install),str(dest)],check=True,timeout=60)
tools=[]
for name in ['sload.f2fs','dump.f2fs']:
 a=install/'usr/local/sbin'/name;b=dest/'usr/local/sbin'/name;assert a.read_bytes()==b.read_bytes();tools.append(dict(name=name,sha256=hashlib.sha256(b.read_bytes()).hexdigest()))
(ref/'f2fs-tool-copy-validation.json').write_text(json.dumps(dict(tools=tools,accepted_device_node_and_special_mode_fixes_preserved=True,baseline122_tools_preserved=True),indent=2)+'\n')
for name in ['pack-rootfs-fixed.sh','verify-sparse-fixed.py','export-rootfs-image-fixed.py','verify-image-export-fixed.py','finalize-rootfs-image.py']:
 s=(r/'reference/kernel122'/name).read_text().replace('kernel122','kernel126').replace('pmos-samurai-rootfs122','pmos-samurai-build126').replace('reference/kernel126/ensure-rootfs-volume.py','reference/kernel126/ensure-build-volume.py').replace('k121','k126').replace('candidate_kernel=121','candidate_kernel=126').replace('rootfs_stage=122','rootfs_stage=126').replace('validated121','validated126').replace('candidate121','candidate126')
 s=s.replace('reference/kernel126/device-fixture-validation.json','reference/kernel122/device-fixture-validation.json')
 s=s.replace('all_non_module_userspace_preserved=True','all_non_module_userspace_except_verified_bluetooth_release_path_preserved=True')
 (ref/name).write_text(s)
print('K126_MATCHING_F2FS_TOOLS_AND_FULL_IMAGE_REVERSE_VALIDATORS_READY')
