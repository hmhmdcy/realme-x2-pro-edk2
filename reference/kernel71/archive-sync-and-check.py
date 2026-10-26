from pathlib import Path
import hashlib, json, shutil, subprocess
r=Path('/mnt/e/edk2-samurai-out/kernel71');w=Path('/mnt/e/RealmeX2Pro edk2')
repo=Path('/home/cy122/edk2-samurai/repo');prefix='Platform/Realme/sm8150/'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='0819bd544089e5120108203f8cd2d5c56e374e23'
assert git('status','--porcelain').decode().strip()=='M Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
docs=['HANDOVER-NEXT.md','README.md','RX-CONSOLE.md','FLYWHEEL.md','DOCS-INDEX.md',
 'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/71-native-s3706-touch-bringup.md',
 'linux-port/README.md','linux-port/docs/00-INDEX.md','linux-port/docs/ROOTFS-PRESERVE-ANDROID.md',
 'linux-port/docs/HARDWARE-STATUS.md','linux-port/dts/sm8150-samurai.dts',
 'linux-port/kernel71-builtins.config','linux-port/patches/0007-input-rmi4-optional-reset-gpio.patch',
 'linux-port/patches/0008-arm64-dts-samurai-s3706-touch.patch']
refs=w/'reference/kernel71';assert {p.name for p in refs.iterdir()}=={'README.md'}
subprocess.run(['python3',str(r/'verify.py')],check=True,stdout=subprocess.DEVNULL)
for source in sorted(r.iterdir()):
 if source.is_file() and source.name!='touch-events.validated.txt' and (
  source.suffix in ('.raw','.txt','.gz','.json','.jsonl','.py','.ps1','.sh','.out','.err','.diff','.dts','.c','.dtb')
  or source.name in ('config-before','config-touch','input-events.bin','core-sources-before.sha256')):
  shutil.copyfile(source,refs/source.name)
names=docs+['reference/kernel71/'+p.name for p in refs.iterdir() if p.is_file()]
for n in names:
 target=repo/prefix/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(w/n,target)
subprocess.run(['git','-C',str(repo),'diff','--check','--',*[prefix+n for n in docs if not n.endswith('.patch')]],check=True)
result=subprocess.run(['bash',str(w/'linux-port/scripts/docs-health-check.sh')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(r/'docs-health-check.txt').write_bytes(result.stdout)
assert result.returncode==0 and b'RESULT: clean' in result.stdout,result.stdout.decode()
shutil.copyfile(r/'docs-health-check.txt',refs/'docs-health-check.txt')
subprocess.run(['python3',str(refs/'verify.py')],check=True,stdout=subprocess.DEVNULL)
(refs/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'
 for p in sorted(refs.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
for n in ('docs-health-check.txt','SHA256SUMS','verification-report.json','dtb-validation.json','input-validation.json'):
 shutil.copyfile(refs/n,repo/prefix/'reference/kernel71'/n)
subprocess.run(['python3',str(refs/'verify.py')],check=True,stdout=subprocess.DEVNULL)
names=docs+['reference/kernel71/'+p.name for p in sorted(refs.iterdir()) if p.is_file()]
paths=[prefix+n for n in names]+[prefix+'FdtBlob/samurai/sm8150-realme-samurai.dtb']
(r/'publish-files.json').write_text(json.dumps(dict(names=names,paths=paths),indent=2)+'\n')
print(f'Docs health clean, standalone evidence/SHA manifest verified: {len(docs)} docs/source files, {len(list(refs.iterdir()))} evidence files.')
