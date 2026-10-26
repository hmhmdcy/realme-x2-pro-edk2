from pathlib import Path
import runpy,subprocess,shutil,json,hashlib,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
build=root/'decode-build';out=Path('/mnt/e/edk2-samurai-out/kernel119/gpu-coredump')
assert (build/'build.ninja').is_file() and shutil.disk_usage(root).free>2*1024**3
env=dict(os.environ,TMPDIR=str(root))
logfile=out/'crashdec-build-private.txt'
if logfile.exists():
    for n in range(1,100):
        prior=out/f'crashdec-build-private-attempt{n}.txt'
        if not prior.exists():logfile.rename(prior);break
with (out/'crashdec-build-private.txt').open('w') as log:
    p=subprocess.run(['ninja','-C',str(build),'-j','4','src/freedreno/decode/crashdec'],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=600)
print('BUILD_EXIT',p.returncode)
print('\n'.join((out/'crashdec-build-private.txt').read_text().splitlines()[-20:]))
assert p.returncode==0
binary=build/'src/freedreno/decode/crashdec';target=out/'crashdec-mesa26.2.4-x86_64'
shutil.copy2(binary,target);target.chmod(0o700)
report=dict(version='26.2.4',only_crashdec_target_built=True,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),phone_unchanged=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119/crashdec-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
