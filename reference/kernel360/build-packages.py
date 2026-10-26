"""Build the complete signed r28/r23 package set on the E-drive image."""
from pathlib import Path
from contextlib import contextmanager
import json,os,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;SDK=storage.SDK;source=storage.candidate();marker=host.PRIVATE/'package-build-state.json'
for name in ['package-source-validation.json','ipa-contract-validation.json']:assert json.loads((HERE/name).read_text())['passed']
if marker.exists() and not json.loads(marker.read_text()).get('terminal'):raise RuntimeError('Inspect the existing process/session before another build')
state=dict(stage=360,pid=os.getpid(),terminal=False,steps=[])
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
@contextmanager
def bind(actual,slot):
    actual.mkdir(exist_ok=True);slot.mkdir(exist_ok=True)
    assert not any(slot.iterdir()) and subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
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
    if code:raise RuntimeError(label+' failed; inspect its log')
save(phase='preparing')
try:
    with storage.sdk_candidate(),bind(source.parent/'packages360-r28',SDK/'packages360-r28'):
        assert not (source/'pkg').exists()
        run(['chroot',str(SDK),'env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec abuild -F -d -K -P /packages360-r28 build rootpkg index'],'framework-build')
    with bind(source.parent/'packages-config360-r28',SDK/'packages-config360-r28'),bind(source.parent/'samurai-camera-config360-r28',SDK/'work/samurai-camera-config360-r28'):
        run(['chroot',str(SDK),'env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config360-r28 && umask 022 && exec abuild -F -d -K -P /packages-config360-r28 all'],'config-build')
except BaseException:save(phase='failed',terminal=True);raise
report=dict(stage=360,framework_version='99990.7.2-r28',configuration_version='0.1.0-r23',steps=state['steps'],sdk_binds_unmounted=True,outputs_on_existing_e_ext4=True,installed=False,passed=True)
(HERE/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');save(phase='complete',terminal=True,exit_code=0);print(json.dumps(report,indent=2))
