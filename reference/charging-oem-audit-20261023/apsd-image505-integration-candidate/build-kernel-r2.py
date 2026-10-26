"""Incremental same-Image build over prepared private copy-up views."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepared505_namespace_inputs',HERE/'prepare-kernel.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
OUT,BASE,base=p.OUT,p.BASE,p.base
sha=p.sha;save=p.save
targets=['drivers/usb/dwc3/'+name+'.o' for name in ['core','trace','gadget','ep0','debugfs','dwc3-qcom','dwc3-qcom-legacy','dwc3-generic-plat','samurai-apsd-owner']]
targets+=['drivers/firmware/efi/'+name+'.o' for name in ['efi','samurai-eud-handoff','samurai-eud-route']]
targets+=['drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o','drivers/tty/serial/eud.o','drivers/tty/serial/eud_earlycon.o','drivers/usb/misc/qcom_eud.o','drivers/usb/typec/tcpm/qcom/qcom_pmic_tcpm.o']
def child(parent,parent_ns,parent_mounts):
 assert os.geteuid()==0 and base.namespace()!=parent_ns
 subprocess.run(['mount','--make-rprivate','/'],check=True)
 for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
  merged=OUT/(name+'-merged');options='lowerdir='+str(BASE/name)+',upperdir='+str(OUT/(name+'-upper'))+',workdir='+str(OUT/(name+'-work'))
  subprocess.run(['mount','-t','overlay','overlay','-o',options,str(merged)],check=True)
  subprocess.run(['mount','--bind',str(merged),str(target)],check=True)
 for source,target in [(BASE/'input-initramfs363',base.PAYLOAD),(OUT/'tmp',base.TEMP)]:
  subprocess.run(['mount','--bind',str(source),str(target)],check=True)
  if target==base.PAYLOAD:subprocess.run(['mount','-o','remount,bind,ro',str(target)],check=True)
 assert p.mount_hash(parent)==parent_mounts
 prepared=json.loads((OUT/'prepared-config-private.json').read_bytes());assert sha(base.BUILD/'.config')==prepared['new_config_sha256']
 for name in p.composition['local_header_additions_after_first_compile']:
  row=p.composition['sources'][name];target=base.SOURCE/name;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((p.ROOT/row['origin']).read_bytes())
 assert all(sha(base.SOURCE/name)==row['sha256'] for name,row in p.composition['sources'].items())
 save(OUT/'build-namespace-proof-private.json',dict(parent_namespace=parent_ns,child_namespace=base.namespace(),parent_mounts_unchanged=True,
   process=p.pid_info(os.getpid()),source_and_build_private_overlays=True,input_initramfs_readonly=True,prepared_config_sha256=sha(base.BUILD/'.config')))
 env=base.build_environment();env.update(KBUILD_BUILD_VERSION='505')
 commands=[]
 def run(name,argv):
  with (OUT/(name+'.log')).open('xb') as log:
   started=time.monotonic();process=subprocess.Popen(argv,cwd=base.BUILD,env=env,stdout=log,stderr=subprocess.STDOUT)
   row=dict(phase=name,process=p.pid_info(process.pid),argv=argv,terminal=False);save(OUT/'build-current-process-private.json',row)
   try:code=process.wait()
   finally:
    row.update(terminal=True,returncode=process.returncode,seconds=time.monotonic()-started);log.flush();os.fsync(log.fileno())
    row['log_sha256']=sha(OUT/(name+'.log'));save(OUT/(name+'-terminal-private.json'),row)
   commands.append(row);save(OUT/'build-r2-commands-private.json',commands);assert code==0,(name,code)
 argv=['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','V=1','-j4']
 run('affected-objects-r2',argv+targets)
 run('Image505-r2',argv+['Image'])
 image=base.BUILD/'arch/arm64/boot/Image';blob=image.read_bytes();assert b'#505 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in blob
 assert (base.BUILD/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
 assert sha(base.BUILD/'.config')==prepared['new_config_sha256']
 for name in ['usr/initramfs_data.cpio','usr/initramfs_inc_data','usr/initramfs_data.o','drivers/power/supply/bq27xxx_battery.o']:
  assert sha(base.BUILD/name)==sha(BASE/'build'/name),name
 def symbols(path):
  rows={}
  for line in path.read_text().splitlines():
   fields=line.split()
   if len(fields)>=4 and fields[2]=='vmlinux':rows[fields[1]]=fields
  return rows
 old,new=symbols(BASE/'build/vmlinux.symvers'),symbols(base.BUILD/'vmlinux.symvers')
 assert old and all(name in new and new[name]==row for name,row in old.items()),'Existing builtin export rows changed'
 added=sorted(set(new)-set(old));assert 'samurai_apsd_bus_register' in added and 'samurai_eud_producer_claim' in added
 output_names=['arch/arm64/boot/Image','vmlinux','vmlinux.symvers','System.map',*targets]
 result=dict(passed=True,commands=commands,private_output=str(OUT),prepared_config_sha256=prepared['new_config_sha256'],required_configs=p.composition['required_config'],
  Image505=dict(sha256=sha(image),bytes=len(blob)),outputs={name:dict(sha256=sha(base.BUILD/name),bytes=(base.BUILD/name).stat().st_size) for name in output_names},
  original_builtin_exports_preserved=len(old),added_builtin_exports=added,source_files=len(p.composition['sources']),
  original_gauge_object_and_initramfs_exact=True,modules_or_firmware_packed=False,DTB_prepared=False,phone_accessed=False,installed=False)
 save(OUT/'kernel-build-private.json',result)
 assert p.mount_hash(parent)==parent_mounts
def main():
 prep=json.loads((HERE/'kernel-preparation-result.json').read_bytes());assert prep['passed']
 original=json.loads((OUT/'kernel-build-terminal-private.json').read_bytes());assert original['terminal'] and original['returncode']==1
 failed=json.loads((OUT/'affected-objects-terminal-private.json').read_bytes());assert failed['terminal'] and failed['returncode']==2
 assert not (OUT/'kernel-build-r2-owner-private.json').exists(),'Observe original build; do not replay'
 helper=p.REF/'kernel284/storage.py';m=p.load('original_storage_505_kernel_build',helper);m.mounted_build()
 before={name:sha(Path(name)) for name in prep['shared_and_baseline_after']}
 parent_ns=base.namespace();parent_mounts=p.mount_hash()
 command=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(os.getpid()),parent_ns,parent_mounts]
 with (OUT/'kernel-build-r2-stdout-private.txt').open('xb') as out,(OUT/'kernel-build-r2-stderr-private.txt').open('xb') as err:
  process=subprocess.Popen(command,stdout=out,stderr=err)
  save(OUT/'kernel-build-r2-owner-private.json',dict(process=p.pid_info(process.pid),command=command,runner_sha256=sha(Path(__file__)),composition_sha256=sha(HERE/'composition.json')))
  try:code=process.wait()
  finally:save(OUT/'kernel-build-r2-terminal-private.json',dict(terminal=True,returncode=process.returncode,pid=process.pid))
 after={name:sha(Path(name)) for name in before}
 result=dict(passed=code==0 and before==after and parent_ns==base.namespace() and parent_mounts==p.mount_hash(),returncode=code,
   shared_and_baseline_before=before,shared_and_baseline_after=after,parent_namespace_unchanged=parent_ns==base.namespace(),parent_mounts_unchanged=parent_mounts==p.mount_hash(),
   private_output=str(OUT),phone_accessed=False,installed=False)
 if code==0:result['build']=json.loads((OUT/'kernel-build-private.json').read_bytes())
 save(HERE/'kernel-build-r2-result.json',result);print(json.dumps(dict(passed=result['passed'],returncode=code,shared_unchanged=before==after,Image505=result.get('build',{}).get('Image505'))))
 if code:print((OUT/'kernel-build-r2-stderr-private.txt').read_text()[-5000:])
 raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--child':child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
 else:main()
