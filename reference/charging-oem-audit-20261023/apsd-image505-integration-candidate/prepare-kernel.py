"""Actual private Kconfig preparation, preserving the current504 lower trees."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REF=ROOT/'reference'
OUT=Path('/home/cy122/charging-management-20261023/apsd-image505-01')
BASE=OUT.parent/'dwc-image504-budget-fence-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('existing_505_baseline_build_environment',REF/'charging-session-20261023/gauge-image363-baseline/run-baseline.py')
assert sha(REF/'charging-session-20261023/gauge-image363-baseline/run-baseline.py')=='136a60e4815014b4fc1afc221f2abfcd39935440def62af081059ee1e2b58650'
composition=json.loads((HERE/'composition.json').read_bytes());assert composition['prepared']
for row in composition['sources'].values():assert sha(ROOT/row['origin'])==row['sha256']
def mount_hash(pid='self'):return hashlib.sha256(('\n'.join(base.mounts(pid))+'\n').encode()).hexdigest()
def pid_info(pid):
 p=Path('/proc',str(pid));fields=(p/'stat').read_text().rsplit(')',1)[1].split()
 return dict(pid=pid,startticks=int(fields[19]))
def child(parent,parent_ns,parent_mounts):
 assert os.getuid()==0 and base.namespace()!=parent_ns
 subprocess.run(['mount','--make-rprivate','/'],check=True)
 assert mount_hash(parent)==parent_mounts
 for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
  options='lowerdir='+str(BASE/name)+',upperdir='+str(OUT/(name+'-upper'))+',workdir='+str(OUT/(name+'-work'))
  merged=OUT/(name+'-merged');subprocess.run(['mount','-t','overlay','overlay','-o',options,str(merged)],check=True)
  subprocess.run(['mount','--bind',str(merged),str(target)],check=True)
 for source,target in [(BASE/'input-initramfs363',base.PAYLOAD),(OUT/'tmp',base.TEMP)]:
  subprocess.run(['mount','--bind',str(source),str(target)],check=True)
  if target==base.PAYLOAD:subprocess.run(['mount','-o','remount,bind,ro',str(target)],check=True)
 assert mount_hash(parent)==parent_mounts
 save(OUT/'namespace-proof-private.json',dict(parent_namespace=parent_ns,child_namespace=base.namespace(),parent_mounts_unchanged=True,
  private_overlay_sources_and_build=True,initramfs_bound_readonly=True,parent_pid=parent,child=pid_info(os.getpid())))
 # Verify a copy-up cannot change the lower inode before running Kbuild.
 probe=base.SOURCE/'drivers/usb/dwc3/core.c';old=sha(BASE/'source354/drivers/usb/dwc3/core.c')
 probe.write_bytes(probe.read_bytes());assert not os.path.samefile(probe,BASE/'source354/drivers/usb/dwc3/core.c') and sha(BASE/'source354/drivers/usb/dwc3/core.c')==old
 for target,row in composition['sources'].items():
  path=base.SOURCE/target;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/row['origin']).read_bytes());assert sha(path)==row['sha256']
 env=base.build_environment();env.update(KBUILD_BUILD_VERSION='505')
 commands=[]
 def run(name,argv):
  with (OUT/(name+'.log')).open('xb') as log:
   started=time.monotonic();process=subprocess.Popen(argv,cwd=base.BUILD,env=env,stdout=log,stderr=subprocess.STDOUT)
   row=dict(phase=name,process=pid_info(process.pid),argv=argv,terminal=False);save(OUT/'current-process-private.json',row)
   try:code=process.wait()
   finally:
    row.update(terminal=True,returncode=process.returncode,seconds=time.monotonic()-started);log.flush();os.fsync(log.fileno())
    save(OUT/(name+'-terminal-private.json'),row)
   commands.append(row);assert code==0,(name,code)
 args=[str(base.SOURCE/'scripts/config'),'--file',str(base.BUILD/'.config')]
 for name,value in composition['required_config'].items():assert value=='y';args+=['--enable',name]
 run('set-profile',args)
 run('olddefconfig',['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','olddefconfig'])
 def config(path):
  values={}
  for line in path.read_text().splitlines():
   if line.startswith('CONFIG_') and '=' in line:key,value=line.split('=',1);values[key]=value
   elif line.startswith('# CONFIG_') and line.endswith(' is not set'):values[line[2:-11]]='n'
  return values
 before=config(BASE/'build/.config');after=config(base.BUILD/'.config')
 assert all(after.get('CONFIG_'+name)==value for name,value in composition['required_config'].items())
 assert not any(value=='y' and after.get(name)!='y' for name,value in before.items()),'Existing builtins must not be dropped'
 delta={name:dict(before=before.get(name,'n'),after=after.get(name,'n')) for name in sorted(set(before)|set(after)) if before.get(name,'n')!=after.get(name,'n')}
 save(OUT/'prepared-config-private.json',dict(passed=True,commands=commands,delta=delta,new_config_sha256=sha(base.BUILD/'.config'),all_original_builtins_retained=True,
    source_files=len(composition['sources']),kernel_or_module_compiled=False,copy_up_verified=True,phone_accessed=False))
 assert mount_hash(parent)==parent_mounts
 print(json.dumps(dict(prepared=True,config_delta=delta,source_files=len(composition['sources']))))
def main():
 helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
 m=load('original_guard_private505_configuration',helper);m.mounted_build()
 assert not OUT.exists() and shutil.disk_usage('/home/cy122').free>4*1024**3
 assert sha(BASE/'build/arch/arm64/boot/Image')=='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'
 OUT.mkdir()
 for name in ['source354','build']:
  for suffix in ['upper','work','merged']:(OUT/(name+'-'+suffix)).mkdir()
 (OUT/'tmp').mkdir()
 watched=[BASE/'build/.config',BASE/'build/Module.symvers',BASE/'build/arch/arm64/boot/Image',base.BUILD/'.config',base.BUILD/'Module.symvers']
 watched+=[BASE/'source354/drivers/usb/dwc3'/name for name in ['core.c','core.h','gadget.c']]
 before={str(path):sha(path) for path in watched};parent_ns=base.namespace();parent_mounts=mount_hash()
 command=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(os.getpid()),parent_ns,parent_mounts]
 with (OUT/'prepare-stdout-private.txt').open('xb') as out,(OUT/'prepare-stderr-private.txt').open('xb') as err:
  process=subprocess.Popen(command,stdout=out,stderr=err);save(OUT/'prepare-owner-private.json',dict(process=pid_info(process.pid),command=command,composition_sha256=sha(HERE/'composition.json')))
  try:code=process.wait()
  finally:save(OUT/'prepare-terminal-private.json',dict(terminal=True,returncode=process.returncode,process_pid=process.pid))
 after={str(path):sha(path) for path in watched}
 result=dict(passed=code==0 and before==after and parent_ns==base.namespace() and parent_mounts==mount_hash(),returncode=code,
  shared_and_baseline_before=before,shared_and_baseline_after=after,parent_namespace_unchanged=parent_ns==base.namespace(),parent_mounts_unchanged=parent_mounts==mount_hash(),
  private_output=str(OUT),kernel_or_firmware_built=False,phone_accessed=False,installed=False)
 save(HERE/'kernel-preparation-result.json',result)
 print(json.dumps(dict(passed=result['passed'],returncode=code,shared_and_baseline_unchanged=before==after)))
 if code:print((OUT/'prepare-stderr-private.txt').read_text()[-5000:])
 raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--child':child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
 else:main()
