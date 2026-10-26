from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',commit,'--','drivers/media/platform/msm/camera/cam_icp'],text=True,timeout=25).splitlines()
paths=[p for p in names if Path(p).name=='cam_ipe_hw_intf.h'];assert len(paths)==1
manifest=json.loads((HERE/'oem-sources.json').read_text())
for path in paths:
 out=P/'oem'/Path(path).name
 if not out.exists():out.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=35))
 raw=out.read_bytes();manifest['files'].append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'oem-sources.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(paths=paths,bytes=len(raw))))
