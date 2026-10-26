from pathlib import Path
import subprocess,runpy,hashlib,json,tarfile,shutil,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs122');root=stage/'rootfs';base=Path('/home/cy122/pmos-samurai-rootfs115/rootfs')
out=Path('/mnt/e/edk2-samurai-out/kernel122');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122')
source=Path('/mnt/e/edk2-samurai-out/kernel121/modules-k121-private.tar.gz');release='7.3.0-rc6-rmx1931-samurai+'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
    return h.hexdigest()
assert not root.exists() and base.is_dir() and shutil.disk_usage(stage).free>15*1024**3
assert sha(source)=='a0d778b79be5f453fb65d0d906e6d23b45197415346be0a56f16920e21971484'
assert sha(base/'usr/lib/modules'/release/'kernel/drivers/net/ipa/ipa.ko')=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
assert sum(line.startswith('P:') for line in (base/'lib/apk/db/installed').read_text().splitlines())==936
assert sha(Path('/mnt/e/edk2-samurai-out/kernel115/samurai-rootfs-f2fs-delay-fixed.simg'))=='d8fc01cea0187b5f1174a910dc01f4f566714716a78debf6061af37d1dd3f1f4'
subprocess.run(['cp','-a',str(base),str(root)],check=True,timeout=300)
module_root=root/'usr/lib/modules'/release
assert module_root.resolve()==stage/'rootfs/usr/lib/modules'/release
shutil.rmtree(module_root)
with tarfile.open(source) as tf:
    members=tf.getmembers()
    assert all(not m.issym() and not m.islnk() and '..' not in Path(m.name).parts and (m.name in ['lib/modules','lib/modules/'+release] or m.name.startswith('lib/modules/'+release+'/')) and (m.isdir() or m.isfile()) for m in members)
    # lib in archive is a logical prefix. Rootfs uses /lib -> usr/lib; extract
    # inside usr, never follow archive-controlled symlinks or paths.
    tf.extractall(root/'usr',members=members,filter='data')
assert len(list(module_root.rglob('*.ko')))==770
assert sha(module_root/'kernel/drivers/net/ipa/ipa.ko')=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
(root/'etc/samurai-rootfs-stage').write_text('rootfs122-kernel121-camera-basis\n')
subprocess.run(['depmod','-b',str(root),release],check=True,timeout=30)
report=dict(rootfs_stage_created=True,userspace_packages=936,whole_kernel121_module_tree_installed=True,module_count=770,ipa_fixed_module_byte_identical_to_running_baseline=True,baseline115_image_and_tree_preserved=True,no_phone_changes=True,hardware_complete=False,goal_complete=False)
(ref/'rootfs-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
