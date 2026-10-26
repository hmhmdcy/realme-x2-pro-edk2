from pathlib import Path
import ast,hashlib,json,runpy,struct,subprocess,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129');stage=Path('/home/cy122/pmos-samurai-kernel129');k=stage/'kernel'
release=(k/'include/config/kernel.release').read_text().strip();assert release=='7.3.0-rc6-rmx1931-samurai-k129+'
assert (out/'depmod-private.txt').stat().st_size==0
for name in ['modules-build-private.log','image-build-private.log']:assert 'error:' not in (out/name).read_text().lower()
banner=[l for l in subprocess.check_output(['strings',str(k/'vmlinux')],text=True).splitlines() if l.startswith('Linux version 7.')];assert banner and all(release in l and '#129 SMP' in l for l in banner)

assert subprocess.check_output(['git','diff','--binary'],cwd=k)==subprocess.check_output(['git','diff','--binary'],cwd=Path('/home/cy122/pmos-samurai-kernel128/kernel'))
code=(r/'reference/kernel126/record-build-and-modules.py').read_text();node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='executable_sections');scope={'struct':struct};exec(ast.get_source_segment(code,node),scope);sections=scope['executable_sections']
def modules(path):
 with tarfile.open(path) as tf:
  result={}
  for m in tf:
   assert (m.isfile() or m.isdir()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
   if m.isfile() and m.name.endswith('.ko'):result[m.name.split('/kernel/',1)[1]]=tf.extractfile(m).read()
 return result
old=modules(out.parent/'kernel128/modules-k128-private.tar.gz');new=modules(out/'modules-k129-private.tar.gz');assert old.keys()==new.keys() and len(new)==770
changed=[name for name in new if sections(old[name])!=sections(new[name])];assert changed==[],changed
for data in new.values():
 start=data.index(b'vermagic=')+9;assert data[start:data.index(0,start)].decode().startswith(release+' ')
for name in ['btbcm','btqca','hci_uart']:assert (stage/f'initramfs/lib/modules/samurai/{name}.ko').read_bytes()==new[f'drivers/bluetooth/{name}.ko']
assert hashlib.sha256((k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()).hexdigest()=='166384b8994883ccb31220fc18c7a94f1f9dcdb8fc2244a4375d7f74d1a4e475'
import sys
sys.path.insert(0,str(ref));from cpio_contract import members,console_ok
oldcpio=members(Path('/home/cy122/pmos-samurai-kernel128/kernel/usr/initramfs_data.cpio'));newcpio=members(k/'usr/initramfs_data.cpio')
assert 'dev/console' not in oldcpio and console_ok(newcpio) and set(newcpio)==set(oldcpio)|{'dev/console'}
changedcpio=[name for name in oldcpio if oldcpio[name]!=newcpio[name]]
assert set(changedcpio)=={'lib/modules/samurai/'+name+'.ko' for name in ['btbcm','btqca','hci_uart']}
for name in ['btbcm','btqca','hci_uart']:assert newcpio['lib/modules/samurai/'+name+'.ko']['sha256']==hashlib.sha256(new['drivers/bluetooth/'+name+'.ko']).hexdigest()
artifacts=[]
for role,path in [('Image',k/'arch/arm64/boot/Image'),('DTB',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')]:
 payload=path.read_bytes();(out/f'{role}-k129-private').write_bytes(payload);artifacts.append(dict(role=role,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
pack=out/'modules-k129-private.tar.gz'
report=dict(candidate=129,release=release,full_image_modules_dtb_build_pass=True,full_banner_matches=True,module_count=770,
 all_770_module_executable_sections_byte_equal128=True,all_module_vermagic_matches=True,matching_initramfs_bt_modules=True,encoded_console_char_5_1_uid_gid_zero_mode0600=True,existing_initramfs_members_preserved_except_matching_bt_vermagic=True,
 fixed_ipa_camss_cphy_cpas_preserved=True,dtb_byte_identical126=True,no_uefi_rebuild_needed=True,
 archive_sha256=hashlib.sha256(pack.read_bytes()).hexdigest(),archive_bytes=pack.stat().st_size,
 artifacts=artifacts,depmod_system_map_no_diagnostics=True,not_deployed=True,goal_complete=False)
(ref/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'candidate-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
