"""Only local Python checks; no phone, kernel mount, build, transport or request creation."""
from pathlib import Path
import hashlib, json, subprocess

HERE = Path(__file__).resolve().parent
OUT = Path('E:/edk2-samurai-out/charging-management-20261023/charger-reattach-update-tests-private-01')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def main():
    OUT.mkdir(mode=0o700, exist_ok=False)
    commands=[]
    for name, args in [('directed', ['test-update.py']), ('default', ['stage-worker.py'])]:
        path='/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/charger-reattach-observation-update-candidate/'+args[0]
        argv=['wsl','-d','Ubuntu','-u','root','--','python3','-B',path]
        with (OUT/(name+'-stdout-private.txt')).open('xb') as stdout, (OUT/(name+'-stderr-private.txt')).open('xb') as stderr:
            child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            try: rc=child.wait()
            finally: child.wait()
        commands.append(dict(argv=argv,pid=child.pid,terminal=True,returncode=rc,
                             stdout_sha256=sha((OUT/(name+'-stdout-private.txt')).read_bytes()),
                             stderr_sha256=sha((OUT/(name+'-stderr-private.txt')).read_bytes())))
        if rc: break
    result=dict(passed=len(commands)==2 and all(c['returncode']==0 for c in commands), commands=commands,
                private_output=str(OUT),device_accessed=False,old_matrices_rerun=False)
    (HERE/'local-check-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result)); return 0 if result['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
