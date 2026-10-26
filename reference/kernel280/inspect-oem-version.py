"""Identify the actual SM8150 IFE family before implementing an ISP backend."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ROOT = Path(__file__).resolve().parent
REPO = Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
COMMIT = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
base = 'drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/'
paths = ['arch/arm64/boot/dts/19781/sm8150-camera.dtsi',
         'arch/arm64/boot/dts/19781/sm8150-v2-camera.dtsi',
         base + 'vfe_hw/vfe17x/cam_vfe17x.c',
         base + 'vfe_hw/vfe17x/cam_vfe175.h',
         base + 'vfe_hw/vfe17x/cam_vfe175_130.h',
         base + 'ife_csid_hw/cam_ife_csid175.h',
         base + 'ife_csid_hw/cam_ife_csid175_200.h',
         base + 'ife_csid_hw/cam_ife_csid_core.c',
         base + 'ife_csid_hw/cam_ife_csid_core.h']
records = {}
for path in paths:
    run = subprocess.run(['git', '-C', str(REPO), 'show', COMMIT + ':' + path], capture_output=True)
    if run.returncode:
        records[path] = dict(error=run.stderr.decode().strip())
        continue
    data = run.stdout
    name = 'oem-' + Path(path).name
    (host.PRIVATE / name).write_bytes(data)
    records[path] = dict(commit=COMMIT, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), local_name=name)
    terms = ['qcom,vfe', 'qcom,csid', 'num_client', 'num_out', 'camif_cmd', 'camif_config',
             'reg_update', 'hw_version', 'ipp_reg', 'pix_store', 'pixel_store']
    hits = [f'{i+1}: {line}' for i, line in enumerate(data.decode().splitlines()) if any(term in line for term in terms)]
    print(Path(path).name + '\n' + '\n'.join(hits[:20]))
(ROOT / 'oem-version-sources.json').write_text(json.dumps(dict(stage=280, sources=records,
    prior_vfe170_hardware_naming_requires_correction=True, no_phone_changes=True), indent=2) + '\n')
