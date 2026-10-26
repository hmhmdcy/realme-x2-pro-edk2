"""Run only affected checks, materialize offline, then inspect local defaults."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-activation-tests-private-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(mode=0o700,exist_ok=False);commands=[]
 for label,name,args in [('delta','test-delta.py',[]),('quiesce-default','eud-quiesce.py',[]),('restart-default','eud-restart.py',[]),
  ('proof-default','stage-proof.py',[]),('materializer-default','materialize.py',[]),('materialize','materialize.py',['--materialize']),('operator-default','fastboot-operator.py',[])]:
  argv=['wsl','-d','Ubuntu','-u','root','--','python3','-B','/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/irq-native-usb-pm-activation-device-candidate/'+name,*args]
  stdout=OUT/(label+'-stdout-private.txt');stderr=OUT/(label+'-stderr-private.txt')
  with stdout.open('xb') as out,stderr.open('xb') as err:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
   try:code=child.wait()
   finally:child.wait()
  commands.append(dict(label=label,argv=argv,pid=child.pid,terminal=True,returncode=code,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
  if code:break
 report=dict(passed=len(commands)==7 and all(x['returncode']==0 for x in commands),commands=commands,private_output=str(OUT),
  device_accessed=False,actual_runtime_guard_or_lease_created=False)
 (HERE/'local-check-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
