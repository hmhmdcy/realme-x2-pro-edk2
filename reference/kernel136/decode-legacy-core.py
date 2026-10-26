from pathlib import Path
import subprocess
import runpy
import os
import resource
import hashlib
import json
import time

r = Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
root = Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = r / 'reference/kernel136'
binary = root / 'decode-build/src/freedreno/decode/crashdec'
core = out / 'devcd2-private.data'
assert hashlib.sha256(core.read_bytes()).hexdigest() == 'ada2ef05da78118a5bf40ae3cd26e4ea3c8a0d30863dd89ad2df6a5e23fe5260'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == json.loads((r / 'reference/kernel119/crashdec-build-validation.json').read_text())['binary_sha256']
def limits():
    for kind, bound in [(resource.RLIMIT_AS,1024**3),(resource.RLIMIT_CPU,40),
                        (resource.RLIMIT_FSIZE,32*1024**2),(resource.RLIMIT_CORE,0)]:
        resource.setrlimit(kind,(bound,bound))
env = dict(os.environ,RNN_PATH=str(root/'mesa-26.2.4/src/freedreno/registers'),
           GALLIUM_DUMP_CPU='false',TMPDIR=str(root))
logfile = out / 'decoded-legacy-core-private.txt'
assert not logfile.exists()
start = time.monotonic()
with logfile.open('w') as log:
    try:
        p = subprocess.run([str(binary),'-s','-f',str(core)],stdout=log,stderr=subprocess.STDOUT,
                           env=env,cwd=root,preexec_fn=limits,timeout=50)
        code = p.returncode
    except subprocess.TimeoutExpired:
        code = 'timeout'
text = logfile.read_text(errors='replace')
report = dict(stage=136,mesa_version='26.2.4',decoder_exit=code,
    wall_seconds=round(time.monotonic()-start,2),output_bytes=logfile.stat().st_size,
    estimated_location_found='ESTIMATED CRASH LOCATION' in text,
    missing_register_database="couldn't find database" in text,
    output_private=True,phone_unchanged=True,goal_complete=False)
(ref / 'decode-legacy-core-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
