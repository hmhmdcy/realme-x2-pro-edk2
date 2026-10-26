from pathlib import Path
import runpy,subprocess,hashlib,json,tarfile,struct
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');runpy.run_path(str(ref/'ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));v=Path('/home/cy122/pmos-samurai-build126');k=v/'kernel';base=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
release=(k/'include/config/kernel.release').read_text().strip();assert release=='7.3.0-rc6-rmx1931-samurai-k126+'
assert 'error:' not in (out/'kernel-full-build.log').read_text().lower() and (out/'depmod-check-private.txt').stat().st_size==0
banner=[line for line in subprocess.check_output(['strings',str(k/'vmlinux')],text=True).splitlines() if line.startswith('Linux version 7.')];assert banner and all(release in line and '#126 SMP' in line for line in banner)
state=json.loads((ref/'tpg-port-validation.json').read_text())
subprocess.run(['git','diff','--check','--',*state['changed_files']],cwd=k,check=True,timeout=90)
with (out/'patch-dry-run-private.txt').open('w') as log:subprocess.run(['patch','--dry-run','-p1','-i',str(ref/'sm8150-tpg-dma-guards-7.3.patch')],cwd=base,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
artifacts=[]
for role,path in [('Image',k/'arch/arm64/boot/Image'),('DTB',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'),('CAMSS',k/'drivers/media/platform/qcom/camss/qcom-camss.ko')]:
 data=path.read_bytes();assert data;(out/(role+'-k126-private')).write_bytes(data);artifacts.append(dict(role=role,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
def archive(stage):
 with tarfile.open(Path(f'/mnt/e/edk2-samurai-out/kernel{stage}/modules-k{stage}-private.tar.gz')) as tf:
  members=tf.getmembers();assert all((m.isfile() or m.isdir()) and not m.issym() and not m.islnk() and '..' not in Path(m.name).parts and not Path(m.name).is_absolute() for m in members)
  modules={m.name.split('/kernel/',1)[1]:tf.extractfile(m).read() for m in members if m.isfile() and m.name.endswith('.ko')};assert len(modules)==770
  return modules
def executable_sections(data):
 assert data[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',data,18)[0]==183
 shoff=struct.unpack_from('<Q',data,40)[0];ents,count,strings=struct.unpack_from('<HHH',data,58);assert ents==64 and shoff+count*ents<=len(data)
 hdr=lambda n:struct.unpack_from('<IIQQQQIIQQ',data,shoff+n*ents)
 nameshdr=hdr(strings);names=data[nameshdr[4]:nameshdr[4]+nameshdr[5]];result={}
 for n in range(count):
  row=hdr(n)
  if row[2]&4:
   name=names[row[0]:names.index(0,row[0])].decode();assert row[4]+row[5]<=len(data);result[name]=data[row[4]:row[4]+row[5]]
 return result
old=archive(125);new=archive(126);assert old.keys()==new.keys()
changed=[name for name in old if executable_sections(old[name])!=executable_sections(new[name])];assert changed==['drivers/media/platform/qcom/camss/qcom-camss.ko'],changed
for name,data in new.items():
 start=data.index(b'vermagic=')+9;assert data[start:data.index(0,start)].decode().startswith(release+' ')
ipa='drivers/net/ipa/ipa.ko';ipa_hash=hashlib.sha256(new[ipa]).hexdigest();assert executable_sections(new[ipa])==executable_sections(old[ipa])
dep=(v/'modules-root/lib/modules'/release/'modules.dep').read_text()
for line in dep.splitlines():
 name,values=line.split(':',1);assert name.removeprefix('kernel/') in new and all(n.removeprefix('kernel/') in new for n in values.split())
pack=out/'modules-k126-private.tar.gz'
report=dict(candidate=126,release=release,full_image_modules_dtb_build_pass=True,full_banner_matches=True,module_count=770,artifacts=artifacts,archive_bytes=pack.stat().st_size,archive_sha256=hashlib.sha256(pack.read_bytes()).hexdigest(),all_module_vermagic_matches=True,no_archive_symlinks=True,all_dependencies_present=True,depmod_system_map_no_diagnostics=True,changed_executable_sections_vs125=changed,other_769_module_executable_sections_byte_equal=True,fixed_ipa_executable_sections_preserved=True,candidate_ipa_full_sha256=ipa_hash,patch_applies_to125=True,source_whitespace_check_pass=True,old118_release_directory_preserved_by_distinct_release=True,camss_enabled_for_tpg=True,not_deployed=True,goal_complete=False)
(ref/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'candidate-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
