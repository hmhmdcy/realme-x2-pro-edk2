from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
directory=P/'oem';directory.mkdir(exist_ok=True)
names=['drivers/media/platform/msm/camera/cam_utils/cam_soc_util.c','drivers/media/platform/msm/camera/cam_smmu/cam_smmu_api.c']
records=[]
for name in names:
 path=directory/Path(name).name
 if not path.exists():path.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+name],timeout=30))
 raw=path.read_bytes();records.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'oem-boot-sources.json').write_text(json.dumps(dict(stage=356,commit=commit,files=records),indent=2)+'\n')
s=(directory/'cam_soc_util.c').read_text().splitlines()
for i,l in enumerate(s):
 if 'request_irq(' in l or 'request_threaded_irq(' in l:print('\n'.join(s[max(0,i-8):i+12]))
s=(directory/'cam_smmu_api.c').read_text().splitlines()
for i,l in enumerate(s):
 if 'int cam_smmu_alloc_qdss' in l:print('\n'.join(s[i:i+100]))
