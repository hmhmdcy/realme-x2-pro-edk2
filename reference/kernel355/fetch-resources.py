from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'oem';directory.mkdir(exist_ok=True)
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
base='drivers/media/platform/msm/camera/cam_icp/'
paths=[base+n for n in ['icp_hw/a5_hw/a5_dev.c','icp_hw/icp_hw_mgr/cam_icp_hw_mgr.c','icp_hw/icp_hw_mgr/cam_icp_hw_mgr.h','icp_hw/ipe_hw/ipe_core.c','icp_hw/ipe_hw/ipe_dev.c','icp_hw/ipe_hw/ipe_soc.c','icp_hw/bps_hw/bps_core.c']]
records=[]
for name in paths:
 path=directory/Path(name).name
 if not path.exists():path.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+name],timeout=25))
 raw=path.read_bytes();records.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'oem-resource-sources.json').write_text(json.dumps(dict(stage=355,commit=commit,files=records),indent=2)+'\n')
print(json.dumps(dict(files=len(records),bytes=sum(r['bytes'] for r in records)),indent=2))
