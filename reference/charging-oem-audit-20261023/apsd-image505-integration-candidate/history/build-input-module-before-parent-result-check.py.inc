"""Build only the current IRQ/PM APSD input against the actual Image505 view."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,struct,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current505_input_build_inputs',HERE/'prepare-kernel.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
KERNEL,BASE,base=p.OUT,p.BASE,p.base
OUT=Path('/home/cy122/charging-management-20261023/apsd-image505-input-01')
sha=p.sha;save=p.save
build=json.loads((HERE/'kernel-build-r2-result.json').read_bytes());assert build['passed']
def section(raw,name):
 assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,18)[0]==183
 offset=struct.unpack_from('<Q',raw,40)[0];size,count,strings_index=struct.unpack_from('<HHH',raw,58)
 assert size==64
 headers=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
 strings=raw[headers[strings_index][4]:headers[strings_index][4]+headers[strings_index][5]]
 for item in headers:
  at=item[0];label=strings[at:strings.index(0,at)].decode()
  if label==name:return raw[item[4]:item[4]+item[5]]
 raise KeyError(name)
def child(parent,parent_ns,parent_mounts):
 assert os.geteuid()==0 and base.namespace()!=parent_ns
 subprocess.run(['mount','--make-rprivate','/'],check=True)
 for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
  options='lowerdir='+str(BASE/name)+',upperdir='+str(KERNEL/(name+'-upper'))+',workdir='+str(KERNEL/(name+'-work'))
  merged=KERNEL/(name+'-merged');subprocess.run(['mount','-t','overlay','overlay','-o',options,str(merged)],check=True)
  subprocess.run(['mount','--bind',str(merged),str(target)],check=True)
 for source,target in [(BASE/'input-initramfs363',base.PAYLOAD),(KERNEL/'tmp',base.TEMP)]:
  subprocess.run(['mount','--bind',str(source),str(target)],check=True)
  if target==base.PAYLOAD:subprocess.run(['mount','-o','remount,bind,ro',str(target)],check=True)
 assert p.mount_hash(parent)==parent_mounts
 assert sha(base.BUILD/'arch/arm64/boot/Image')==build['build']['Image505']['sha256']
 assert sha(base.BUILD/'.config')==build['build']['prepared_config_sha256']
 assert all(sha(base.SOURCE/name)==row['sha256'] for name,row in p.composition['sources'].items())
 save(OUT/'namespace-proof-private.json',dict(parent_namespace=parent_ns,child_namespace=base.namespace(),parent_mounts_unchanged=True,process=p.pid_info(os.getpid())))
 old=(base.BUILD/'Module.symvers').read_text();known={line.split()[1] for line in old.splitlines() if line.split()}
 symbols=(base.BUILD/'vmlinux.symvers').read_text();rows=[line for line in symbols.splitlines() if line.split() and line.split()[1] not in known]
 names={line.split()[1] for line in rows};assert {'samurai_apsd_bus_register','samurai_apsd_bus_unregister'}<=names
 extra=OUT/'new-builtin-only.symvers';extra.write_text('\n'.join(rows)+'\n')
 env=base.build_environment();env.update(KBUILD_BUILD_VERSION='505')
 argv=['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'M='+str(OUT/'source'),'KBUILD_EXTRA_SYMBOLS='+str(extra),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','V=1','-j4','modules']
 with (OUT/'module-build.log').open('xb') as log:
  started=time.monotonic();process=subprocess.Popen(argv,cwd=base.BUILD,env=env,stdout=log,stderr=subprocess.STDOUT)
  row=dict(process=p.pid_info(process.pid),argv=argv,terminal=False);save(OUT/'current-process-private.json',row)
  try:code=process.wait()
  finally:
   row.update(terminal=True,returncode=process.returncode,seconds=time.monotonic()-started);log.flush();os.fsync(log.fileno());save(OUT/'make-terminal-private.json',row)
 assert code==0,code
 diagnostics=[line for line in (OUT/'module-build.log').read_text(errors='replace').splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()];assert not diagnostics,diagnostics
 raw_module=OUT/'source/samurai-usb-input.ko';installed=OUT/'install/samurai-usb-input.ko';installed.parent.mkdir()
 strip=subprocess.run(['aarch64-linux-gnu-strip','--strip-debug','-o',str(installed),str(raw_module)],capture_output=True,text=True)
 save(OUT/'strip-terminal-private.json',dict(returncode=strip.returncode,stderr=strip.stderr));assert strip.returncode==0 and not strip.stderr
 raw=installed.read_bytes();note=section(raw,'.note.gnu.build-id');assert note==section(raw_module.read_bytes(),'.note.gnu.build-id')
 info=[word.decode() for word in section(raw,'.modinfo').split(b'\0') if word]
 vermagic=[word.removeprefix('vermagic=') for word in info if word.startswith('vermagic=')];assert len(vermagic)==1 and vermagic[0].startswith('7.3.0-rc6-rmx1931-samurai-k363+ ')
 assert 'license=GPL' in info and 'depends=' in info
 imports=[line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(installed)],text=True).splitlines() if len(line.split())>=2 and line.split()[-2]=='U']
 builtin={line.split()[1] for line in symbols.splitlines() if line.split()}
 assert all(name in builtin for name in imports),set(imports)-builtin
 assert {'samurai_apsd_bus_register','samurai_apsd_bus_unregister'}<=set(imports)
 metadata=OUT/'kernel-metadata';metadata.mkdir()
 for name in ['modules.builtin','modules.builtin.modinfo']:(metadata/name).write_bytes((base.BUILD/name).read_bytes())
 before=(BASE/'build/modules.builtin').read_text().splitlines();after=(metadata/'modules.builtin').read_text().splitlines()
 assert set(before)<=set(after)
 assert sha(base.BUILD/'arch/arm64/boot/Image')==build['build']['Image505']['sha256'] and sha(base.BUILD/'.config')==build['build']['prepared_config_sha256']
 result=dict(passed=True,make=row,source_files=p.composition['external_input_module_sources'],new_builtin_symbol_rows=len(rows),
  module=dict(path=str(installed),sha256=sha(installed),bytes=installed.stat().st_size,build_id_note_sha256=hashlib.sha256(note).hexdigest(),vermagic=vermagic[0],strong_import_count=len(imports)),
  actual_Image505=build['build']['Image505'],all_strong_imports_in_actual_Image505=True,actual_APSD_owner_imports=True,module_dependencies=[],
  raw_builtin_metadata={name:dict(path=str(metadata/name),sha256=sha(metadata/name),bytes=(metadata/name).stat().st_size) for name in ['modules.builtin','modules.builtin.modinfo']},
  added_builtin_paths=sorted(set(after)-set(before)),all_previous_builtin_paths_retained=True,Image505_config_unchanged=True,
  private_output=str(OUT),phone_accessed=False,installed=False)
 save(OUT/'result-private.json',result)
 assert p.mount_hash(parent)==parent_mounts
def main():
 helper=p.REF/'kernel284/storage.py';m=p.load('original_storage_505_input_module',helper);m.mounted_build()
 assert not OUT.exists() and shutil.disk_usage('/home/cy122').free>2*1024**3;OUT.mkdir();(OUT/'source').mkdir()
 for name,row in p.composition['external_input_module_sources'].items():
  source=p.ROOT/row['origin'];assert sha(source)==row['sha256'];(OUT/'source'/name).write_bytes(source.read_bytes())
 (OUT/'source/Makefile').write_text('obj-m += samurai-usb-input.o\nccflags-y += -Werror\n')
 watched=build['shared_and_baseline_after'];before={name:sha(Path(name)) for name in watched}
 parent_ns=base.namespace();parent_mounts=p.mount_hash()
 argv=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(os.getpid()),parent_ns,parent_mounts]
 with (OUT/'stdout-private.txt').open('xb') as out,(OUT/'stderr-private.txt').open('xb') as err:
  process=subprocess.Popen(argv,stdout=out,stderr=err);save(OUT/'owner-private.json',dict(process=p.pid_info(process.pid),argv=argv,source_sha256=sha(Path(__file__))))
  try:code=process.wait()
  finally:save(OUT/'terminal-private.json',dict(terminal=True,returncode=process.returncode,pid=process.pid))
 after={name:sha(Path(name)) for name in watched}
 result=dict(passed=code==0 and before==after and parent_ns==base.namespace() and parent_mounts==p.mount_hash(),returncode=code,
  original_shared_and_baseline_before=before,original_shared_and_baseline_after=after,parent_namespace_unchanged=parent_ns==base.namespace(),parent_mounts_unchanged=parent_mounts==p.mount_hash())
 if code==0:result.update(json.loads((OUT/'result-private.json').read_bytes()))
 save(HERE/'input-module-build-result.json',result)
 print(json.dumps(dict(passed=result['passed'],returncode=code,module=result.get('module'),added_builtin_paths=result.get('added_builtin_paths'))))
 if code:print((OUT/'stderr-private.txt').read_text()[-4000:])
 raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--child':child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
 else:main()
