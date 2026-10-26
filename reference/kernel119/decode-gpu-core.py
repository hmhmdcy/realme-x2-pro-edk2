from pathlib import Path
import subprocess,runpy,os,resource,hashlib,json,time,re
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
out=Path('/mnt/e/edk2-samurai-out/kernel119/gpu-coredump')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
binary=root/'decode-build/src/freedreno/decode/crashdec'
core=out/'devcd2-private.data'
assert hashlib.sha256(core.read_bytes()).hexdigest()=='5f6399437cb255c9e78cd53395133993b7016fdc999a174db4e60951eadccc6a'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==json.loads((ref/'crashdec-build-validation.json').read_text())['binary_sha256']
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(40,40))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
env=dict(os.environ,RNN_PATH=str(root/'mesa-26.2.4/src/freedreno/registers'),GALLIUM_DUMP_CPU='false',TMPDIR=str(root))
logfile=out/'decoded-summary-private.txt'
assert not logfile.exists(),'preserve prior decode; use a new prefix for another attempt'
start=time.monotonic()
with logfile.open('w') as log:
    try:
        p=subprocess.run([str(binary),'-s','-f',str(core)],stdout=log,stderr=subprocess.STDOUT,env=env,cwd=root,preexec_fn=limits,timeout=50)
        code=p.returncode
    except subprocess.TimeoutExpired:code='timeout'
text=logfile.read_text(errors='replace')
report=dict(mesa_version='26.2.4',core_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),decoder_exit=code,wall_seconds=round(time.monotonic()-start,2),output_bytes=logfile.stat().st_size,estimated_location_found='ESTIMATED CRASH LOCATION' in text,missing_register_database='couldn\'t find database' in text,output_private=True,phone_unchanged=True)
for path in [out/'decode-validation.json',ref/'decode-validation.json']:path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
