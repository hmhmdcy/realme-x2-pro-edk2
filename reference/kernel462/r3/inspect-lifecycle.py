"""Capture only the actual IMX471/CAMSS/V4L2 lifetime paths, read-only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inspect462r3_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();SOURCE=SHARED.parent/'source354'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r3');PRIVATE.mkdir(parents=True,exist_ok=True,mode=0o700)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
assert shutil.disk_usage(SHARED).free>=2*1024**3
for part in ['r1','r2']:
    public=HERE.parent if part=='r1' else HERE.parent/'r2'
    record=load(public/(part+'-final-validation.json'))
    assert record==load(PRIVATE.parent/('' if part=='r1' else part)/(part+'-frozen-files-private.json'))
    for name,digest in record['files'].items():assert sha(public/name)==digest
commit=load(HERE.parents[1]/'kernel363/boot-candidate-build-validation.json')['commit']
files=['drivers/media/platform/qcom/camss/camss.c','drivers/media/platform/qcom/camss/camss-video.c',
       'drivers/media/v4l2-core/v4l2-async.c','drivers/media/v4l2-core/v4l2-device.c',
       'drivers/media/v4l2-core/v4l2-subdev.c','drivers/media/v4l2-core/v4l2-dev.c',
       'drivers/media/v4l2-core/v4l2-fh.c','drivers/media/v4l2-core/v4l2-ctrls-core.c',
       'drivers/media/v4l2-core/v4l2-ctrls-api.c','include/media/v4l2-subdev.h',
       'include/media/v4l2-device.h','include/media/v4l2-ctrls.h','drivers/base/dd.c',
       'drivers/media/v4l2-core/v4l2-event.c']
rows=[]
for name in files:
    path=SOURCE/name;dst=PRIVATE/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(path.read_bytes())
    pinned=subprocess.check_output(['git','-C',str(SOURCE),'show',commit+':'+name])
    old=PRIVATE/'original363'/name;old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(pinned)
    rows.append(dict(path=name,source_sha256=sha(path),bytes=path.stat().st_size,equal_image363_source=pinned==path.read_bytes()))
candidate=PRIVATE.parent/'r2/candidate/drivers/media/i2c/imx471.c'
copy=PRIVATE/'r2-imx471-private.c';copy.write_bytes(candidate.read_bytes())
(PRIVATE/'source-lifetime-inspection-private.json').write_text(json.dumps(dict(files=rows,commit=commit,
    source_head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip(),
    r2_imx471_sha256=sha(candidate),free_bytes=shutil.disk_usage(SHARED).free),indent=2)+'\n')
rg=shutil.which('rg')
if rg:
    patterns=subprocess.run([rg,'-l',r'\.release\s*=|kref_',str(SOURCE/'drivers/media/i2c')],capture_output=True,text=True,check=True).stdout.splitlines()
else:
    patterns=[str(p) for p in (SOURCE/'drivers/media/i2c').glob('*.c') if re.search(r'\.release\s*=|kref_',p.read_text())]
print(json.dumps(dict(files=rows,r2_imx471_sha256=sha(candidate),free_bytes=shutil.disk_usage(SHARED).free,
                     sensor_release_or_kref_sources=patterns)),flush=True)
