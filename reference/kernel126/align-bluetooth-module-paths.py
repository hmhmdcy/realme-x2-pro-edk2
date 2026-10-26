from pathlib import Path
import runpy,json,struct,ast,hashlib,tarfile,shutil,difflib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');runpy.run_path(str(ref/'ensure-build-volume.py'));v=Path('/home/cy122/pmos-samurai-build126');assert not (ref/'bluetooth-release-validation.json').exists()
# Reuse only the ELF executable-section reader, without rerunning the recorder.
source=(ref/'record-build-and-modules.py').read_text();tree=ast.parse(source);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='executable_sections');scope={'struct':struct};exec(ast.get_source_segment(source,func),scope);sections=scope['executable_sections']
with tarfile.open(out/'modules-k126-private.tar.gz') as tf:modules={Path(m.name).stem:tf.extractfile(m).read() for m in tf if m.isfile() and m.name.endswith('.ko') and '/drivers/bluetooth/' in m.name}
checks=[]
for name in ['btqca','btbcm','hci_uart']:
 old=v/'rootfs/usr/lib/modules/samurai'/(name+'.ko');new=modules[name];assert sections(old.read_bytes())==sections(new),name
 init=v/'initramfs/lib/modules/samurai'/(name+'.ko');assert init.is_file() and sections(init.read_bytes())==sections(new),name
 init.write_bytes(new);checks.append(dict(module=name,old_custom_executable_sections_identical_to_candidate=True,new_sha256=hashlib.sha256(new).hexdigest()))
patch=''
for path in [v/'rootfs/usr/sbin/samurai-bluetooth',v/'initramfs/usr/sbin/samurai-bluetooth']:
 old=path.read_text();needle='"/lib/modules/samurai/$module.ko"';assert old.count(needle)==1
 # Keep the initramfs's minimal legacy directory as its explicit fallback.
 replacement='"/lib/modules/$(uname -r)/kernel/drivers/bluetooth/$module.ko"'
 new=old.replace(needle,replacement)
 line='            /bin/insmod '+replacement
 assert line in new
 new=new.replace(line,'            path="/lib/modules/$(uname -r)/kernel/drivers/bluetooth/$module.ko"\n            [ -f "$path" ] || path="/lib/modules/samurai/$module.ko"\n            /bin/insmod "$path"')
 path.write_text(new);patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+str(path.relative_to(v)),tofile='b/'+str(path.relative_to(v))))
 subprocess_check=__import__('subprocess');subprocess_check.run(['sh','-n',str(path)],check=True)
shutil.copyfile(out/'kernel-full-build.log',out/'first-distinct-release-before-bt-initramfs-build-private.log')
(ref/'bluetooth-release-path.patch').write_text(patch)
(ref/'bluetooth-release-validation.json').write_text(json.dumps(dict(modules=checks,three_old_custom_executable_sections_preserved=True,initramfs_three_modules_now_matching126_vermagic=True,rootfs_bluetooth_uses_current_release_directory=True,diagnostic_initramfs_legacy_fallback_preserved=True,old_live_bluetooth_not_modified_yet=True,kernel_image_rebuild_required=True,phone_unchanged=True),indent=2)+'\n');print('K126_BT_THREE_MODULES_FUNCTION_BYTES_MATCH_AND_RELEASE_PATHS_ALIGNED')
