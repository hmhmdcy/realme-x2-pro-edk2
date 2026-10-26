"""Normal signed abuild using retained objects; preserve the original SDK work."""
from pathlib import Path
import json,os,shutil,subprocess,sys,time,traceback
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=SDK/'work/libcamera';snapshot=SDK/'private/libcamera-before316-r25'
cache=SDK/'work/libcamera278-r24-r3-built';retained=SDK/'work/libcamera316-r25-built'
recipe=SDK/'work/libcamera316-r25';marker=host.PRIVATE/'package-build-state.json'
resume='--resume' in sys.argv
assert work.is_dir() and cache.is_dir() and not snapshot.exists() and retained.exists()==resume
for p in [work,snapshot,retained,cache,recipe]:assert p.parent.resolve().is_relative_to(SDK.resolve()) and not p.is_symlink()
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip() in ['ninja','meson','abuild','cc1plus'] and (p/'cwd').resolve().is_relative_to(work):raise RuntimeError('Existing SDK build is live')
 except (FileNotFoundError,ProcessLookupError):pass
prior=json.loads(marker.read_text())['steps'] if resume else []
state=dict(stage=316,pid=os.getpid(),terminal=False,phase='preparing',steps=prior)
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
def run(args,label):
 attempt=1
 while (host.PRIVATE/(label+f'-r{attempt}.log')).exists():attempt+=1
 log=host.PRIVATE/(label+f'-r{attempt}.log');start=time.monotonic()
 with log.open('xb') as output:
  child=subprocess.Popen(args,stdout=output,stderr=subprocess.STDOUT)
  save(phase=label,child_pid=child.pid,log=str(log));code=child.wait()
 state['steps'].append(dict(name=label,exit_code=code,seconds=round(time.monotonic()-start,2)));save()
 if code:raise RuntimeError(label+' failed; inspect '+str(log))
save();os.rename(work,snapshot)
try:
 save(phase='resume-retained-candidate' if resume else 'copy-retained-cache')
 if resume:os.rename(retained,work)
 else:shutil.copytree(cache,work,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
 # abuild splits packages by moving files. Previous split directories must
 # be regenerated, while src/output retains all compiler objects.
 staging=work/'pkg'
 if staging.exists():
  assert staging.resolve()==work.resolve()/'pkg' and not staging.is_symlink()
  shutil.rmtree(staging)
 for p in recipe.iterdir():
  if p.is_file():shutil.copyfile(p,work/p.name)
 source=work/'src/libcamera-v0.7.2'
 if not resume:run(['patch','--batch','--forward','-p1','-d',str(source),'-i',str(work/'0029-camss-hardware-pipeline.patch')],'patch-apply')
 command=['chroot',str(SDK),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c',
          'cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages316-r25 build rootpkg index']
 run(command,'framework-build')
except BaseException:
 save(phase='failed',terminal=True,exit_code=1)
 raise
finally:
 if work.exists():os.rename(work,retained)
 if snapshot.exists():os.rename(snapshot,work)
 save(original_work_restored=work.exists() and not snapshot.exists(),retained_candidate=str(retained))
try:
 run(['chroot',str(SDK),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c',
      'cd /work/samurai-camera-config316-r25 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config316-r25 all'],'config-build')
 packages=[*sorted((SDK/'packages316-r25').rglob('*.apk')),*sorted((SDK/'packages-config316-r25').rglob('*.apk'))]
 report=dict(stage=316,framework_version='99990.7.2-r25',configuration_version='0.1.0-r20',packages=[p.name for p in packages],steps=state['steps'],
  prior_feature_set_retained=True,original_sdk_work_restored=state['original_work_restored'],installed=False)
 (HERE/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 save(phase='complete',terminal=True,exit_code=0)
 print(json.dumps(report,indent=2))
except BaseException:
 save(phase='failed',terminal=True,exit_code=1);raise
