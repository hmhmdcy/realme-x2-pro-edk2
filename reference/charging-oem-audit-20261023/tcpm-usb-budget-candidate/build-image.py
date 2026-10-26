"""Build two affected objects and Image508 over the frozen R2 private layers."""
from pathlib import Path
import importlib.util,json,os,re,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('budget506_build',HERE.parent/'eud-route-pm-candidate/build-image-r2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p,base=m.p,m.base
OUT=Path('/home/cy122/charging-management-20261023/tcpm-usb-budget-image508-01')
LAYERS=[OUT.parent/x for x in ['tcpm-sink-shutdown-objects-02','tcpm-sink-shutdown-image507-01',
 'tcpm-sink-shutdown-objects-01','tcpm-sink-image507-01','tcpm-sink-port-object-01']]+[m.OUT,m.PREVIOUS,m.LOWER]
CHANGED=json.loads((HERE/'source.json').read_bytes())['sources']
OBJECTS=['drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.o','drivers/usb/typec/tcpm/tcpm.o']
EXACT=['.config','usr/initramfs_data.cpio','usr/initramfs_inc_data','usr/initramfs_data.o',
 'drivers/power/supply/bq27xxx_battery.o','modules.builtin','modules.builtin.modinfo','vmlinux.symvers']
def lower(name,relative):
 for layer in LAYERS:
  q=layer/(name+'-upper')/relative
  if q.exists():return q
 return m.BASE/name/relative
def child(parent,ns,mounts):
 assert os.geteuid()==0 and base.namespace()!=ns
 subprocess.run(['mount','--make-rprivate','/'],check=True)
 for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
  layers=[str(x/(name+'-upper')) for x in LAYERS]+[str(m.BASE/name)]
  opts='lowerdir='+':'.join(layers)+',upperdir='+str(OUT/(name+'-upper'))+',workdir='+str(OUT/(name+'-work'))
  subprocess.run(['mount','-t','overlay','overlay','-o',opts,str(OUT/(name+'-merged'))],check=True)
  subprocess.run(['mount','--bind',str(OUT/(name+'-merged')),str(target)],check=True)
 subprocess.run(['mount','--bind',str(m.BASE/'input-initramfs363'),str(base.PAYLOAD)],check=True)
 subprocess.run(['mount','-o','remount,bind,ro',str(base.PAYLOAD)],check=True)
 subprocess.run(['mount','--bind',str(OUT/'tmp'),str(base.TEMP)],check=True)
 assert p.mount_hash(parent)==mounts
 for target,row in CHANGED.items():
  path=base.SOURCE/target;assert m.sha(path)==row['baseline_sha256'],target
  path.write_bytes((HERE/row['file']).read_bytes());assert m.sha(path)==row['candidate_sha256']
 env=base.build_environment();env['KBUILD_BUILD_VERSION']='508'
 argv=['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
       'LOCALVERSION=+','W=1','-j4'];stages=[]
 for name,targets in [('objects',OBJECTS),('image',['Image'])]:
  started=time.monotonic()
  with (OUT/(name+'.log')).open('xb') as log:
   proc=subprocess.Popen(argv+targets,env=env,stdout=log,stderr=subprocess.STDOUT)
   m.save(OUT/'process.json',dict(process=p.pid_info(proc.pid),argv=argv+targets))
   code=proc.wait()
  diagnostics=[x for x in (OUT/(name+'.log')).read_text().splitlines() if re.search(r'\b(warning:|error:|undefined reference)',x,re.I)]
  stage=dict(name=name,returncode=code,seconds=time.monotonic()-started,diagnostics=diagnostics)
  m.save(OUT/(name+'-terminal.json'),stage);stages.append(stage)
  assert code==0 and not diagnostics,stage
 image=base.BUILD/'arch/arm64/boot/Image'
 assert b'#508 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in image.read_bytes()
 for name in EXACT:assert m.sha(base.BUILD/name)==m.sha(lower('build',name)),name
 m.save(OUT/'child-result.json',dict(passed=True,stages=stages,objects={n:m.sha(base.BUILD/n) for n in OBJECTS},
  Image_path=str(OUT/'build-upper/arch/arm64/boot/Image'),Image_sha256=m.sha(image),Image_bytes=image.stat().st_size,
  exact_inputs=EXACT,sources={n:m.sha(base.SOURCE/n) for n in CHANGED}))
def main():
 assert not OUT.exists() and not (HERE/'build-result.json').exists()
 tests=json.loads((HERE/'test-result.json').read_bytes());assert tests['passed']
 for row in CHANGED.values():assert tests['source_sha256'][row['file']]==m.sha(HERE/row['file'])
 assert json.loads((HERE.parent/'tcpm-sink-shutdown-candidate/build-r2-result.json').read_bytes())['passed']
 p.load('budget_storage',ROOT/'reference/kernel284/storage.py').mounted_build()
 assert os.statvfs('/home/cy122').f_bavail*os.statvfs('/home/cy122').f_frsize>2*1024**3
 tracked=[lower('source354',n) for n in CHANGED]+[lower('build',n) for n in EXACT+['arch/arm64/boot/Image']]
 before={str(q):m.sha(q) for q in tracked};ns,mounts=base.namespace(),p.mount_hash()
 OUT.mkdir()
 for name in ['source354-upper','source354-work','source354-merged','build-upper','build-work','build-merged','tmp']:(OUT/name).mkdir()
 argv=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(os.getpid()),ns,mounts]
 with (OUT/'owner.stdout').open('xb') as stdout,(OUT/'owner.stderr').open('xb') as stderr:
  proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr);m.save(OUT/'owner.json',dict(process=p.pid_info(proc.pid),argv=argv));code=proc.wait()
 after={str(q):m.sha(q) for q in tracked}
 result=dict(passed=code==0 and before==after and ns==base.namespace() and mounts==p.mount_hash(),returncode=code,
  private_output=str(OUT),parent_inputs_unchanged=before==after,parent_mounts_unchanged=mounts==p.mount_hash(),phone_accessed=False,installed=False)
 if code==0:result['build']=json.loads((OUT/'child-result.json').read_bytes())
 m.save(OUT/'terminal.json',dict(terminal=True,returncode=code));m.save(HERE/'build-result.json',result)
 print(json.dumps(result),flush=True)
 if code:print((OUT/'owner.stderr').read_text()[-4000:])
 raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':
 if sys.argv[1:2]==['--child']:child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
 else:main()
