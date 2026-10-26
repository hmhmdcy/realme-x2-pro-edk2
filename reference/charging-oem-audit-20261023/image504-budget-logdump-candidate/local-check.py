"""Run only the actual default read-only carrier check, preserving its real child."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
HERE=Path(__file__).resolve().parent
OUT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image504-budget-logdump-private-01')
assert sys.platform.startswith('linux') and not sys.flags.optimize
assert not OUT.exists() and not OUT.is_symlink(), 'Unique output exists; do not reuse'
argv=[sys.executable,'-B',str(HERE/'package-logdump.py')]
start=time.monotonic();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL)
stdout,stderr=child.communicate();rc=child.wait()
assert rc==0 and not stderr,(rc,stderr.decode(errors='replace'))
actual=json.loads(stdout)
assert actual==dict(checked=True,Image504_proof_ready=True,new_Image_read=True,tools_executed=False,unique_private_exists=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(passed=True,mode='actual default check-local; no tools run',
    original_child=dict(pid=child.pid,argv=argv,terminal=True,returncode=rc,seconds=time.monotonic()-start),
    package_sha256=sha(HERE/'package-logdump.py'),pins_sha256=sha(HERE/'Image504-pins.json'),
    actual_stdout=actual,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest(),
    original_saved502_FAT_and_actual504_Image_read=True,unique_OUT_absent_at_check=True,
    private_output_created=False,tools_storage_SDK_Git_or_device_invoked=False)
(HERE/'local-check-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
