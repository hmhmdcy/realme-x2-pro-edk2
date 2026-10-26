from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root/'reference/kernel74'
kernel = Path('/home/cy122/x2pro-linux/linux')
patch = root/'linux-port/patches/0010-drm-msm-sm8150-command-boot-handoff.patch'
names = ['dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_hw_intf.c','dpu_hw_intf.h']
with tempfile.TemporaryDirectory(prefix='k74-patch-',dir='/home/cy122/x2pro-linux') as directory:
    work = Path(directory)
    for name in names:
        path = 'drivers/gpu/drm/msm/disp/dpu1/'+name
        target = work/path
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ref/(name+'.before'),target)
    subprocess.run(['git','apply','--check',str(patch)],cwd=work,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=work,check=True)
    for name in names:
        path = 'drivers/gpu/drm/msm/disp/dpu1/'+name
        assert (work/path).read_bytes() == (kernel/path).read_bytes(), name
        assert (ref/(name+'.after')).read_bytes() == (kernel/path).read_bytes(), name
result = dict(patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
    check_pass=True,applied_files_match_actual_source=True,changed_files=names)
(ref/'patch-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
