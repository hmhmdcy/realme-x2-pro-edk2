"""Pin GPL CAMIF and bus programming sources from the existing factory repository."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ROOT = Path(__file__).resolve().parent
REPO = Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
COMMIT = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
base = 'drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/'
paths = [base + 'vfe_top/cam_vfe_camif_ver2.c', base + 'vfe_top/cam_vfe_camif_ver2.h',
         base + 'vfe_bus/cam_vfe_bus_ver2.c', base + 'vfe_bus/cam_vfe_bus_ver2.h',
         base + 'vfe17x/cam_vfe175.h']
records = {}
for path in paths:
    data = subprocess.check_output(['git', '-C', str(REPO), 'show', COMMIT + ':' + path])
    name = 'oem-' + Path(path).name
    (host.PRIVATE / name).write_bytes(data)
    records[path] = dict(commit=COMMIT, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), local_name=name)
(ROOT / 'oem-programming-sources.json').write_text(json.dumps(dict(stage=281, sources=records), indent=2) + '\n')
print(json.dumps(records, indent=2))
