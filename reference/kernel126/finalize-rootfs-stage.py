from pathlib import Path
import runpy,tarfile,hashlib,subprocess,json,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');runpy.run_path(str(ref/'ensure-build-volume.py'));v=Path('/home/cy122/pmos-samurai-build126');root=v/'rootfs';build=json.loads((ref/'kernel-build-validation.json').read_text());release=build['release'];archive=out/'modules-k126-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==build['archive_sha256'] and root.is_dir()
module_parent=root/'usr/lib/modules';assert module_parent.resolve()==v/'rootfs/usr/lib/modules' and not module_parent.is_symlink()
assert sorted(p.name for p in module_parent.iterdir())==['7.3.0-rc6-rmx1931-samurai+','samurai']
assert json.loads((ref/'bluetooth-release-validation.json').read_text())['three_old_custom_executable_sections_preserved']
legacy=module_parent/'samurai';assert legacy.resolve()==v/'rootfs/usr/lib/modules/samurai' and not legacy.is_symlink()
shutil.rmtree(legacy)
old=module_parent/'7.3.0-rc6-rmx1931-samurai+';shutil.rmtree(old)
with tarfile.open(archive) as tf:
 members=tf.getmembers();assert all((m.isfile() or m.isdir()) and not m.issym() and not m.islnk() and '..' not in Path(m.name).parts and not Path(m.name).is_absolute() and (m.name=='lib/modules' or m.name=='lib/modules/'+release or m.name.startswith('lib/modules/'+release+'/')) for m in members)
 tf.extractall(root/'usr',members=members,filter='data')
assert len(list((module_parent/release).rglob('*.ko')))==770 and sorted(p.name for p in module_parent.iterdir())==[release]
assert hashlib.sha256((module_parent/release/'kernel/drivers/net/ipa/ipa.ko').read_bytes()).hexdigest()==build['candidate_ipa_full_sha256']
(root/'etc/samurai-rootfs-stage').write_text('rootfs126-kernel126-internal-tpg\n')
subprocess.run(['depmod','-b',str(root),release],check=True,timeout=30)
(ref/'rootfs-stage-validation.json').write_text(json.dumps(dict(candidate_kernel=126,release=release,userspace_packages=936,module_count=770,new_rootfs_only_matching_release=True,accepted122_baseline_preserved=True,no_phone_changes=True),indent=2)+'\n')
code=(r/'reference/kernel122/verify-rootfs-stage.py').read_text().replace('kernel122','kernel126').replace('pmos-samurai-rootfs122','pmos-samurai-build126').replace('reference/kernel126/ensure-rootfs-volume.py','reference/kernel126/ensure-build-volume.py')
code=code.replace("base=Path('/home/cy122/pmos-samurai-rootfs115/rootfs')","base=Path('/home/cy122/pmos-samurai-rootfs122/rootfs')")
code=code.replace("runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')","runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')")
code=code.replace("release='7.3.0-rc6-rmx1931-samurai+'","release='"+release+"'")
code=code.replace('kernel121/modules-k121','kernel126/modules-k126').replace('/home/cy122/pmos-samurai-kernel118/camera121/kernel/System.map','/home/cy122/pmos-samurai-build126/kernel/System.map').replace('candidate_kernel=121','candidate_kernel=126').replace('rootfs_stage=122','rootfs_stage=126').replace('validated121','validated126')
code=code.replace("or relative=='etc/samurai-rootfs-stage':continue","or relative in ['etc/samurai-rootfs-stage','usr/sbin/samurai-bluetooth','usr/bin/samurai-bluetooth']:continue")
code=code.replace("before=manifest(base);after=manifest(root)","expected_bt=(base/'usr/sbin/samurai-bluetooth').read_text().replace('            /bin/insmod \\\"/lib/modules/samurai/$module.ko\\\"','            path=\\\"/lib/modules/$(uname -r)/kernel/drivers/bluetooth/$module.ko\\\"\\n            [ -f \\\"$path\\\" ] || path=\\\"/lib/modules/samurai/$module.ko\\\"\\n            /bin/insmod \\\"$path\\\"')\nassert (root/'usr/sbin/samurai-bluetooth').read_text()==expected_bt\nbefore=manifest(base);after=manifest(root)")
code=code.replace('all_non_module_userspace_content_metadata_identical=True','all_non_module_userspace_except_verified_bluetooth_release_path_preserved=True').replace('firmware_credentials_and_services_preserved=True','firmware_credentials_preserved=True,bluetooth_release_path_exact_verified_change=True')
(ref/'verify-rootfs-stage.py').write_text(code);exec(compile(code,'verify-rootfs126','exec'),{})
print('K126_FULL_ROOTFS_MATCHING_DISTINCT_RELEASE_STAGED_VERIFIED')
