"""Local Python composition/default checks only; no request, lease or transport."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-stage-tests-private-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(mode=0o700,exist_ok=False);commands=[]
    for label,name in [('composition','test-stage.py'),('default','stage-worker.py')]:
        argv=['wsl','-d','Ubuntu','-u','root','--','python3','-B','/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate/'+name]
        stdout=OUT/(label+'-stdout-private.txt');stderr=OUT/(label+'-stderr-private.txt')
        with stdout.open('xb') as out,stderr.open('xb') as err:
            p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
            try:rc=p.wait()
            finally:p.wait()
        commands.append(dict(argv=argv,pid=p.pid,terminal=True,returncode=rc,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
        if rc:break
    r=dict(passed=len(commands)==2 and all(x['returncode']==0 for x in commands),commands=commands,private_output=str(OUT),device_accessed=False,old_matrices_rerun=False)
    (HERE/'local-check-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
