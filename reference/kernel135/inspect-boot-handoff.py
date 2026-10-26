from pathlib import Path
import hashlib
import json
import runpy
import urllib.request
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
out.mkdir(mode=0o700, exist_ok=True)
assert not (ref / 'boot-handoff-source-validation.json').exists()
runpy.run_path(str(r / 'reference/kernel134/ensure-build-volume.py'))
base = Path('/home/cy122/pmos-samurai-build134/usb134/kernel')
sha = lambda b: hashlib.sha256(b).hexdigest()
records = []
for name in ['dpu_hw_ctl.c', 'dpu_hw_ctl.h', 'dpu_hw_intf.c', 'dpu_rm.c', 'dpu_kms.c', 'catalog/dpu_5_0_sm8150.h']:
    p = base / 'drivers/gpu/drm/msm/disp/dpu1' / name
    data = p.read_bytes()
    dest = out / ('current134-' + name.replace('/', '--'))
    assert not dest.exists()
    dest.write_bytes(data)
    records.append(dict(role='current134', source=name, bytes=len(data), sha256=sha(data)))
commit = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
for name in ['sde_hw_ctl.c', 'sde_hw_intf.c', 'sde_encoder_phys_cmd.c']:
    url = f'https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/{commit}/drivers/gpu/drm/msm/sde/{name}'
    try:
        data = urllib.request.urlopen(url, timeout=30).read()
    except Exception as e:
        records.append(dict(role='oem', source=name, url=url, download_error=type(e).__name__))
        continue
    dest = out / ('oem-' + name)
    assert not dest.exists()
    dest.write_bytes(data)
    records.append(dict(role='oem', source=name, url=url, bytes=len(data), sha256=sha(data)))
report = dict(stage=135, current_kernel=134, current_source_snapshots=6, oem_commit=commit,
              sources=records, phone_unchanged=True, root_cause_proven=False,
              display_boot_fix_accepted=False, goal_complete=False)
(ref / 'boot-handoff-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K135_FIXED_CURRENT134_AND_OEM_HANDOFF_SOURCE_CAPTURED', flush=True)
