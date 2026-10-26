"""Reuse only the local original SM8150 ICP programming sources needed here."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'oem';directory.mkdir(exist_ok=True)
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
base='drivers/media/platform/msm/camera/cam_icp/'
paths=['arch/arm64/boot/dts/qcom/sm8150-camera.dtsi','arch/arm64/boot/dts/qcom/sm8150-v2-camera.dtsi']+[base+p for p in ['icp_hw/a5_hw/a5_core.c','icp_hw/a5_hw/a5_core.h','icp_hw/a5_hw/a5_soc.c','hfi.c','fw_inc/hfi_intf.h','fw_inc/hfi_reg.h','fw_inc/hfi_sys_defs.h','fw_inc/hfi_session_defs.h']]
records=[]
for path in paths:
 target=directory/Path(path).name
 if not target.exists():target.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=25))
 raw=target.read_bytes();records.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'oem-icp-sources.json').write_text(json.dumps(dict(stage=352,commit=commit,repository='retained Realme downstream kernel mirror used in281',files=records),indent=2)+'\n')
print(json.dumps(dict(files=len(records),bytes=sum(r['bytes'] for r in records),commit=commit),indent=2))
