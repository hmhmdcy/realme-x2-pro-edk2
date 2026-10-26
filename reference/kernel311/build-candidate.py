"""Build the isolated candidate; system libraries and kernel remain untouched."""
from pathlib import Path
import json,shutil,subprocess,time
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE=SDK/'work/libcamera299-inline'
sources={'include/libcamera/ipa/camss.mojom':HERE/'camss.mojom'}
for directory,target in [('ipa','src/ipa/camss-vfe'),('pipeline','src/libcamera/pipeline/camss-vfe')]:
    for p in (HERE/directory).iterdir():
        if p.is_file():sources[target+'/'+p.name]=p
sources['include/linux/qcom-camss-config.h']=Path('/home/cy122/x2pro-linux/camera309-link-kernel/include/uapi/linux/qcom-camss-config.h')
for name,source in sources.items():
    destination=TREE/name
    if not destination.exists() or destination.read_bytes()!=source.read_bytes():
        shutil.copyfile(source,destination)
attempt=1
while (host.PRIVATE/f'build-r{attempt}.log').exists():attempt+=1
log=host.PRIVATE/f'build-r{attempt}.log'
start=time.monotonic()
with log.open('xb') as output:
    child=subprocess.Popen(['chroot',str(SDK),'/usr/bin/ninja','-C','/work/libcamera299-inline/output','-j6'],
                           stdout=output,stderr=subprocess.STDOUT)
    (host.PRIVATE/'build-state.json').write_text(json.dumps({'pid':child.pid,'terminal':False})+'\n')
    code=child.wait()
report={'stage':311,'attempt':attempt,'exit_code':code,'seconds':round(time.monotonic()-start,2),
        'installed':False,'source_files':list(sources)}
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(host.PRIVATE/'build-state.json').write_text(json.dumps({'pid':child.pid,'terminal':True,**report})+'\n')
print(log.read_text(errors='replace')[-6000:])
print(json.dumps(report,indent=2))
raise SystemExit(code)
