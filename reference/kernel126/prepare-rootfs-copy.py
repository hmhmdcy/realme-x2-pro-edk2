from pathlib import Path
import runpy,subprocess,hashlib,json,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';runpy.run_path(str(ref/'ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
v=Path('/home/cy122/pmos-samurai-build126');source=Path('/home/cy122/pmos-samurai-rootfs122/rootfs');root=v/'rootfs'
assert not root.exists() and shutil.disk_usage(v).free>15*1024**3
assert sum(line.startswith('P:') for line in (source/'lib/apk/db/installed').read_text().splitlines())==936
assert hashlib.sha256((source/'usr/lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko').read_bytes()).hexdigest()=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
subprocess.run(['cp','-a',str(source),str(root)],check=True,timeout=300)
(ref/'rootfs-copy-validation.json').write_text(json.dumps(dict(accepted122_source_preserved=True,userspace_packages=936,new_e_rootfs_copy_created=True,modules_not_finalized_yet=True,phone_unchanged=True),indent=2)+'\n');print('K126_COMPLETE_ACCEPTED_USERSPACE_COPY_CREATED')
