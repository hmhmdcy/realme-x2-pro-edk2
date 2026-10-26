from pathlib import Path
import hashlib
import json
import runpy
import urllib.request
r=Path('/mnt/e/RealmeX2Pro edk2')
ref=r/'reference/kernel135'
out=Path('/mnt/e/edk2-samurai-out/kernel135/audio-next-source')
assert not out.exists()
out.mkdir(mode=0o700)
runpy.run_path(str(r/'reference/kernel134/ensure-build-volume.py'))
k=Path('/home/cy122/pmos-samurai-build134/usb134/kernel')
records=[]
for name in ['drivers/mfd/wcd934x.c','sound/soc/codecs/wcd934x.c','drivers/slimbus/messaging.c','drivers/slimbus/qcom-ngd-ctrl.c']:
    p=k/name
    if not p.exists():
        records.append(dict(path=name,exists=False))
        continue
    data=p.read_bytes()
    (out/name.replace('/','--')).write_bytes(data)
    records.append(dict(path=name,exists=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
local=(k/'drivers/mfd/wcd934x.c').read_text()
assert 'devm_regmap_add_irq_chip' in local and 'static void wcd934x_slim_status_down' not in local
url='https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2603.1/03387.html'
try:
    data=urllib.request.urlopen(url,timeout=30).read()
    (out/'upstream-cleanup-mail-private.html').write_bytes(data)
    download=dict(url=url,downloaded=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
except Exception as e:
    download=dict(url=url,downloaded=False,error=type(e).__name__)
report=dict(stage=135,source_snapshots=records,upstream_mail=download,upstream_patch_subject='mfd: wcd934x: Unroll regmap and irqchip on removal',current_mfd_cleanup_fix_absent=True,current_status_down_only_removes_children=True,current_regmap_and_irqchip_failure_cleanup_missing=True,specific_efuse_enospc_root_cause_proven=False,next_candidate_requires_separate_build_and_real_boot=True,phone_unchanged=True,goal_complete=False)
(ref/'next-audio-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
