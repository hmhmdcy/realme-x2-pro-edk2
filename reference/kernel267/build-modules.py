"""Build three in-tree modules and restore every touched source/output."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import resource
import shutil
import stat
import subprocess
import time

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel267')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
spec = importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
before = helper.snapshot()
out = P/'modules-build-r1';out.mkdir(mode=0o700)
mapping = {'imx319.c':'drivers/media/i2c/imx319.c',
           'imx319-222mhz-tables.h':'drivers/media/i2c/imx319-222mhz-tables.h',
           'qcom-pm8008.c':'drivers/mfd/qcom-pm8008.c',
           'qcom-pm8008-regulator.c':'drivers/regulator/qcom-pm8008-regulator.c'}
prefixes = {'drivers/media/i2c':('imx319','.imx319'),
            'drivers/mfd':('qcom-pm8008','.qcom-pm8008'),
            'drivers/regulator':('qcom-pm8008','.qcom-pm8008')}
def outputs():
    return {p for d,starts in prefixes.items() for p in (K/d).iterdir()
            if p.is_file() and p.name.startswith(starts)}
names = ['.config','.config.old','Module.symvers','modules.order','include/generated/compile.h',
         'include/generated/utsversion.h','include/generated/autoconf.h','include/config/auto.conf',
         'include/config/auto.conf.cmd','include/config/kernel.release']
saved = {str(p.relative_to(K)):(p.read_bytes(),stat.S_IMODE(p.stat().st_mode))
         for p in outputs()|{K/n for n in names} if p.is_file()}
backup = out/'before';backup.mkdir(mode=0o700)
for n,(data,mode) in saved.items():
    p=backup/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={n:sha(R/n) for n in mapping}
for n in mapping:shutil.copyfile(R/n,out/(n+'-input-private'))
targets=['drivers/mfd/qcom-pm8008.ko','drivers/regulator/qcom-pm8008-regulator.ko','drivers/media/i2c/imx319.ko']
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
ret=None;start=time.monotonic()
try:
    for n,d in mapping.items():shutil.copyfile(R/n,K/d)
    with (out/'build-private.log').open('xb') as log:
        ret=subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
         'LD=aarch64-linux-gnu-ld --no-keep-memory','CONFIG_VIDEO_IMX319=m','W=1','-j3',*targets],
         cwd=K,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit).returncode
    if ret==0:
        for t in targets:
            dest=out/Path(t).name;shutil.copyfile(K/t,dest)
            subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
    for p in outputs():
        if str(p.relative_to(K)) not in saved:p.unlink()
    for n,(data,mode) in saved.items():
        p=K/n;p.write_bytes(data);p.chmod(mode)
    exact=before==helper.snapshot()
    (out/'restoration-private.json').write_text(json.dumps(dict(build_exit=ret,canonical_restored=exact))+'\n')
    assert exact
assert ret==0,'Build failed; canonical restored; inspect private log'
diagnostics=[l for l in (out/'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):',l,re.I)]
assert not diagnostics,diagnostics
available={l.split()[1] for l in saved['Module.symvers'][0].decode().splitlines()}
vermagic=json.loads((R.parent/'kernel228/intree-build-validation.json').read_text())['vermagic']
modules={}
for t in targets:
    p=out/Path(t).name
    info=lambda key:subprocess.check_output(['modinfo','-F',key,str(p)],text=True).strip()
    imports={l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(p)],text=True).splitlines() if l.strip()}
    assert imports<=available and info('intree')=='Y' and info('vermagic')==vermagic
    modules[p.name]=dict(sha256=sha(p),bytes=p.stat().st_size,intree='Y',vermagic=vermagic,imports_available=True)
report=dict(stage=267,modules=modules,source_inputs=inputs,w1_diagnostics=0,canonical_restored=True,
            hardware_not_yet_executed=True,elapsed_seconds=round(time.monotonic()-start,2))
(R/'module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
