from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-cold-rollback-tests-private-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(mode=0o700,exist_ok=False);commands=[]
 for label,name in [('affected','test-rollback.py'),('default','restore-worker.py')]:
  argv=['wsl','-d','Ubuntu','-u','root','--','python3','-B','/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/irq-native-usb-pm-cold-rollback-candidate/'+name]
  stdout=OUT/(label+'-stdout-private.txt');stderr=OUT/(label+'-stderr-private.txt')
  with stdout.open('xb') as out,stderr.open('xb') as err:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
   try:code=child.wait()
   finally:child.wait()
  commands.append(dict(label=label,argv=argv,pid=child.pid,terminal=True,returncode=code,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
  if code:break
 result=dict(passed=len(commands)==2 and all(x['returncode']==0 for x in commands),commands=commands,private_output=str(OUT),device_accessed=False)
 (HERE/'local-check-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
