"""Build matching 313 IPA + 315 handler and standard event timestamp signal."""
from pathlib import Path
import json,shutil,subprocess,time
import host
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kernel313'
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE=SDK/'work/libcamera299-inline'
sources={'include/libcamera/ipa/camss.mojom':OLD/'camss.mojom'}
for directory,target,stage in [('ipa','src/ipa/camss-vfe',OLD),('pipeline','src/libcamera/pipeline/camss-vfe',HERE)]:
 for p in (stage/directory).iterdir():
  if p.is_file():sources[target+'/'+p.name]=p
for p in (HERE/'framework').rglob('*'):
 if p.is_file():sources[p.relative_to(HERE/'framework').as_posix()]=p
sources['include/linux/qcom-camss-config.h']=Path('/home/cy122/x2pro-linux/camera309-link-kernel/include/uapi/linux/qcom-camss-config.h')
for name,source in sources.items():
 destination=TREE/name
 if not destination.exists() or destination.read_bytes()!=source.read_bytes():shutil.copyfile(source,destination)
attempt=1
while (host.PRIVATE/f'build-r{attempt}.log').exists():attempt+=1
log=host.PRIVATE/f'build-r{attempt}.log';start=time.monotonic()
with log.open('xb') as output:
 child=subprocess.Popen(['chroot',str(SDK),'/usr/bin/ninja','-C','/work/libcamera299-inline/output','-j6'],stdout=output,stderr=subprocess.STDOUT)
 (host.PRIVATE/'build-state.json').write_text(json.dumps(dict(pid=child.pid,terminal=False))+'\n')
 code=child.wait()
report=dict(stage=315,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),installed=False,source_files=list(sources),ipa_stage=313,kernel_stage=314)
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(host.PRIVATE/'build-state.json').write_text(json.dumps(dict(pid=child.pid,terminal=True,**report))+'\n')
print(log.read_text(errors='replace')[-7500:]);print(json.dumps(report,indent=2))
raise SystemExit(code)
