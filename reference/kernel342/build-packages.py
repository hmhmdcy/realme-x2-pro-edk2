from pathlib import Path
from contextlib import contextmanager
import json,os,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;SDK=storage.SDK;source=storage.candidate();marker=host.PRIVATE/'package-build-state.json'
if marker.exists() and not json.loads(marker.read_text()).get('terminal'):raise RuntimeError('Inspect existing build handle')
state=dict(stage=342,pid=os.getpid(),terminal=False,steps=[])
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
@contextmanager
def repository(name):
 actual=source.parent/name;slot=SDK/name;actual.mkdir(exist_ok=True);slot.mkdir(exist_ok=True);assert not any(slot.iterdir())
 subprocess.run(['mount','--bind',str(actual),str(slot)],check=True,capture_output=True)
 try:yield
 finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
def run(args,label):
 attempt=1
 while (host.PRIVATE/(label+f'-r{attempt}.log')).exists():attempt+=1
 start=time.monotonic()
 with (host.PRIVATE/(label+f'-r{attempt}.log')).open('xb') as log:
  child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT);save(phase=label,child_pid=child.pid,log=str(log.name));code=child.wait()
 state['steps'].append(dict(name=label,exit_code=code,seconds=round(time.monotonic()-start,2)));save()
 if code:raise RuntimeError(label+' failed')
save(phase='preparing')
try:
 with storage.sdk_candidate(),repository('packages342-r27'):
  assert not (source/'pkg').exists()
  run(['chroot',str(SDK),'env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec abuild -F -d -K -P /packages342-r27 build rootpkg index'],'framework-build')
 with repository('packages-config342-r27'):
  run(['chroot',str(SDK),'env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config342-r27 && umask 022 && exec abuild -F -d -K -P /packages-config342-r27 all'],'config-build')
except BaseException:save(phase='failed',terminal=True);raise
report=dict(stage=342,framework_version='99990.7.2-r27',configuration_version='0.1.0-r22',steps=state['steps'],sdk_binds_unmounted=True,outputs_on_existing_e_ext4=True,installed=False)
(HERE/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');save(phase='complete',terminal=True,exit_code=0);print(json.dumps(report,indent=2))
