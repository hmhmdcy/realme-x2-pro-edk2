"""Build only the changed506 objects and Image in a private overlay over505."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE.parent/'apsd-image505-integration-candidate'
spec=importlib.util.spec_from_file_location('frozen505_kernel_environment',OLD/'prepare-kernel.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
base=p.base;OUT=Path('/home/cy122/charging-management-20261023/route-pm-image506-01');LOWER=p.OUT;BASE=p.BASE
sha=p.sha;save=p.save
CHANGED={'drivers/firmware/efi/samurai-eud-route.c':'samurai-eud-route.c','include/linux/usb/samurai-eud-route.h':'samurai-eud-route.h','drivers/usb/dwc3/samurai-apsd-owner.c':'samurai-apsd-owner.c'}
def lower_file(name,relative):
 q=LOWER/(name+'-upper')/relative
 return q if q.exists() else BASE/name/relative
def exports(path):
 rows={}
 for line in path.read_text().splitlines():
  v=line.split()
  if len(v)>=4 and v[2]=='vmlinux':rows[v[1]]=v
 return rows
def child(parent,parent_ns,parent_mounts):
 assert os.geteuid()==0 and base.namespace()!=parent_ns
 subprocess.run(['mount','--make-rprivate','/'],check=True)
 for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
  options='lowerdir='+str(LOWER/(name+'-upper'))+':'+str(BASE/name)+',upperdir='+str(OUT/(name+'-upper'))+',workdir='+str(OUT/(name+'-work'))
  subprocess.run(['mount','-t','overlay','overlay','-o',options,str(OUT/(name+'-merged'))],check=True)
  subprocess.run(['mount','--bind',str(OUT/(name+'-merged')),str(target)],check=True)
 for source,target in [(BASE/'input-initramfs363',base.PAYLOAD),(OUT/'tmp',base.TEMP)]:
  subprocess.run(['mount','--bind',str(source),str(target)],check=True)
  if target==base.PAYLOAD:subprocess.run(['mount','-o','remount,bind,ro',str(target)],check=True)
 assert p.mount_hash(parent)==parent_mounts
 for target,name in CHANGED.items():
  path=base.SOURCE/target;assert path.exists();path.write_bytes((HERE/name).read_bytes());assert sha(path)==sha(HERE/name)
 cfg=sha(base.BUILD/'.config');assert cfg==sha(lower_file('build','.config'))
 env=base.build_environment();env['KBUILD_BUILD_VERSION']='506'
 argv=['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','V=1','-j4']
 commands=[]
 for name,targets in [('changed-objects',['drivers/firmware/efi/samurai-eud-route.o','drivers/usb/dwc3/samurai-apsd-owner.o']),('Image506',['Image'])]:
  with (OUT/(name+'.log')).open('xb') as log:
   started=time.monotonic();process=subprocess.Popen(argv+targets,cwd=base.BUILD,env=env,stdout=log,stderr=subprocess.STDOUT)
   entry=dict(name=name,process=p.pid_info(process.pid),terminal=False,argv=argv+targets);save(OUT/'current-process.json',entry)
   ret=process.wait();log.flush();os.fsync(log.fileno());entry.update(terminal=True,returncode=ret,seconds=time.monotonic()-started)
   commands.append(entry);save(OUT/(name+'-terminal.json'),entry);assert ret==0,(name,ret)
  diagnostics=[line for line in (OUT/(name+'.log')).read_text().splitlines() if re.search(r'\b(warning:|error:|undefined reference)',line,re.I)]
  assert not diagnostics,diagnostics
 image=base.BUILD/'arch/arm64/boot/Image';raw=image.read_bytes();assert b'#506 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in raw
 assert cfg==sha(base.BUILD/'.config') and (base.BUILD/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
 unchanged=['usr/initramfs_data.cpio','usr/initramfs_inc_data','usr/initramfs_data.o','drivers/power/supply/bq27xxx_battery.o','modules.builtin','modules.builtin.modinfo']
 for name in unchanged:assert sha(base.BUILD/name)==sha(lower_file('build',name)),name
 old,new=exports(lower_file('build','vmlinux.symvers')),exports(base.BUILD/'vmlinux.symvers');assert old==new and old
 result=dict(passed=True,private_output=str(OUT),Image506=dict(path=str(OUT/'build-upper/arch/arm64/boot/Image'),sha256=sha(image),bytes=len(raw)),commands=commands,config_sha256=cfg,builtin_exports_exact=len(old),gauge_initramfs_and_builtin_metadata_exact=unchanged,changed_sources={target:sha(HERE/name) for target,name in CHANGED.items()},phone_accessed=False,installed=False)
 save(OUT/'child-result.json',result)
def main():
 assert not OUT.exists() and not (HERE/'image-build-result.json').exists()
 assert json.loads((HERE/'provider-test-result.json').read_bytes())['passed'] and json.loads((HERE/'owner-test-result.json').read_bytes())['passed']
 helper=ROOT/'reference/kernel284/storage.py';m=p.load('original506_storage',helper);m.mounted_build()
 assert os.statvfs('/home/cy122').f_bavail*os.statvfs('/home/cy122').f_frsize>2*1024**3
 prep=json.loads((OLD/'kernel-preparation-result.json').read_bytes())
 tracked=set(prep['shared_and_baseline_after'])
 tracked.update(str(lower_file('build',name)) for name in ['.config','arch/arm64/boot/Image','vmlinux.symvers','modules.builtin','modules.builtin.modinfo'])
 tracked.update(str(lower_file('source354',target)) for target in CHANGED)
 before={name:sha(Path(name)) for name in sorted(tracked)};ns=base.namespace();mounts=p.mount_hash()
 OUT.mkdir()
 for name in ['source354-upper','source354-work','source354-merged','build-upper','build-work','build-merged','tmp']:(OUT/name).mkdir()
 cmd=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(os.getpid()),ns,mounts]
 with (OUT/'owner.stdout').open('xb') as out,(OUT/'owner.stderr').open('xb') as err:
  process=subprocess.Popen(cmd,stdout=out,stderr=err);save(OUT/'owner.json',dict(process=p.pid_info(process.pid),argv=cmd))
  ret=process.wait();save(OUT/'terminal.json',dict(returncode=ret,terminal=True,pid=process.pid))
 after={name:sha(Path(name)) for name in before}
 result=dict(passed=ret==0 and before==after and ns==base.namespace() and mounts==p.mount_hash(),returncode=ret,parent_inputs_before=before,parent_inputs_after=after,parent_inputs_unchanged=before==after,parent_mounts_unchanged=mounts==p.mount_hash(),private_output=str(OUT),source505_unmodified=True,phone_accessed=False)
 if ret==0:result['build']=json.loads((OUT/'child-result.json').read_bytes())
 save(HERE/'image-build-result.json',result);print(json.dumps(dict(passed=result['passed'],returncode=ret,Image506=result.get('build',{}).get('Image506'))),flush=True)
 if not result['passed']:print((OUT/'owner.stderr').read_text()[-6000:])
 raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':
 if sys.argv[1:2]==['--child']:child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
 else:main()
