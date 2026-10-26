from pathlib import Path
import json,os,shutil,subprocess,time
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=SDK/'work/libcamera';retained=SDK/'work/libcamera321-lsc-built';snapshot=SDK/'private/libcamera-before321-packages';recipe=SDK/'work/libcamera321-r26'
assert work.is_dir() and retained.is_dir() and not snapshot.exists()
marker=host.PRIVATE/'package-build-state.json'
if marker.exists() and not json.loads(marker.read_text()).get('terminal'):raise RuntimeError('Inspect existing package build first')
state=dict(stage=321,pid=os.getpid(),terminal=False,steps=[])
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
def run(args,label):
 attempt=1
 while (host.PRIVATE/(label+f'-r{attempt}.log')).exists():attempt+=1
 start=time.monotonic()
 with (host.PRIVATE/(label+f'-r{attempt}.log')).open('xb') as log:
  child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT);save(phase=label,child_pid=child.pid,log=str(log.name));code=child.wait()
 state['steps'].append(dict(name=label,exit_code=code,seconds=round(time.monotonic()-start,2)));save()
 if code:raise RuntimeError(label+' failed')
save(phase='preparing');os.rename(work,snapshot)
try:
 os.rename(retained,work)
 staging=work/'pkg'
 if staging.exists():
  assert staging.resolve()==work.resolve()/'pkg' and not staging.is_symlink();shutil.rmtree(staging)
 for p in recipe.iterdir():
  if p.is_file():shutil.copyfile(p,work/p.name)
 run(['chroot',str(SDK),'env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec abuild -F -d -K -P /packages321-r26 build rootpkg index'],'framework-build')
except BaseException:
 save(phase='failed',terminal=True);raise
finally:
 if work.exists():os.rename(work,retained)
 if snapshot.exists():os.rename(snapshot,work)
 save(original_work_restored=work.is_dir() and not snapshot.exists())
try:
 run(['chroot',str(SDK),'env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config321-r26 && umask 022 && exec abuild -F -d -K -P /packages-config321-r26 all'],'config-build')
 report=dict(stage=321,framework_version='99990.7.2-r26',configuration_version='0.1.0-r21',steps=state['steps'],original_sdk_work_restored=state['original_work_restored'],installed=False)
 (HERE/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');save(phase='complete',terminal=True,exit_code=0);print(json.dumps(report,indent=2))
except BaseException:
 save(phase='failed',terminal=True);raise
