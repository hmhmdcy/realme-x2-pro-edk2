from pathlib import Path
import runpy,subprocess,os,resource,json,hashlib
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
source=root/'mesa-26.2.4';binary=root/'decode-build/src/freedreno/decode/crashdec'
out=Path('/mnt/e/edk2-samurai-out/kernel119/gpu-coredump')
env=dict(os.environ,RNN_PATH=str(source/'src/freedreno/registers'),GALLIUM_DUMP_CPU='false',TMPDIR=str(root))
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(25,25))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
results=[]
for name in ['crash','crash_prefetch']:
    trace=source/f'src/freedreno/tests/traces/{name}.devcore'
    expected=source/f'src/freedreno/tests/reference/{name}.log'
    logfile=out/f'fixture-{name}-private.txt';err=out/f'fixture-{name}-private.err'
    assert trace.is_file() and expected.is_file()
    with logfile.open('w') as log,err.open('w') as stderr:
        p=subprocess.run([str(binary),'-sf',str(trace)],stdout=log,stderr=stderr,env=env,cwd=source,preexec_fn=limits,timeout=30)
    equal=logfile.read_bytes()==expected.read_bytes()
    results.append(dict(name=name,exit=p.returncode,exact_reference_match=equal,actual_sha256=hashlib.sha256(logfile.read_bytes()).hexdigest(),expected_sha256=hashlib.sha256(expected.read_bytes()).hexdigest(),stderr_bytes=err.stat().st_size))
report=dict(upstream_fixture_results=results,all_exact_pass=all(r['exit']==0 and r['exact_reference_match'] for r in results),phone_unchanged=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119/crashdec-fixtures-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
