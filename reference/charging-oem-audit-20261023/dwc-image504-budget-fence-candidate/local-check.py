"""Actual default runner check and Linux unique-output lstat; no storage/build."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01')
assert sys.platform.startswith('linux') and not sys.flags.optimize
assert not OUT.exists() and not OUT.is_symlink(), 'Unique output already exists; do not reuse it'
argv=[sys.executable,'-B',str(HERE/'run-504.py')]
start=time.monotonic();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL)
stdout,stderr=child.communicate();rc=child.wait()
assert rc==0 and not stderr,(rc,stderr.decode(errors='replace'))
actual=json.loads(stdout);assert actual==dict(passed=True,mode='check-local',storage_or_build_invoked=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(schema='samurai-image504-budget-fence-local-check-v1',passed=True,
    original_child=dict(pid=child.pid,argv=argv,terminal=True,returncode=rc,seconds=time.monotonic()-start),
    runner_sha256=sha(HERE/'run-504.py'),actual_stdout=actual,
    stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest(),
    unique_private_output=str(OUT),output_absent_at_check=True,private_output_created=False,
    storage_or_build_or_device_invoked=False)
(HERE/'local-check-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
