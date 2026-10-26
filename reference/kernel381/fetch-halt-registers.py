from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
paths=['drivers/media/platform/msm/camera/cam_cdm/'+n for n in ['cam_hw_cdm170_reg.h','cam_cdm_hw_core.c']]
manifest=json.loads((HERE/'oem-sources.json').read_text())
for path in paths:
 out=P/'oem'/Path(path).name
 if not out.exists():out.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=35))
 raw=out.read_bytes();manifest['files'].append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'oem-sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';directory=source/'drivers/media/platform/qcom/camss';found=[]
for path in directory.iterdir():
 if path.is_file() and path.suffix in ['.c','.h'] and any(s in path.name for s in ['cpas','camnoc']):
  (P/(path.name+'.before')).write_bytes(path.read_bytes());found.append(path.name)
print(json.dumps(dict(oem_files=paths,shared_camss_resources=found)))
