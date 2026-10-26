from pathlib import Path
import hashlib, shutil, subprocess

w=Path('/mnt/e/RealmeX2Pro edk2')
ref=w/'reference/kernel75'
out=Path('/mnt/e/edk2-samurai-out/kernel75')
repo=Path('/home/cy122/edk2-samurai/repo')
platform=repo/'Platform/Realme/sm8150'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()=='20a1d6041b0f4a5b3eb384372de65c22ff2ab81e'
status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
assert status=='M Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb',status
for pattern in ('*-flash-validation.json','*-build.log','final-native*.events.txt',
                'final-native*.txt','final-reboot-native*.events.txt','final-reboot-native*.txt'):
    for p in out.glob(pattern):
        assert p.stat().st_size<2*1024*1024,p
        shutil.copyfile(p,ref/p.name)
for n in ('firmware-validation.json','current-facts.txt','final-firmware-audit.txt'):
    shutil.copyfile(out/n,ref/n)
shutil.copyfile(out/'config-before',ref/'kernel-final.config')
for p in ref.rglob('*'):
    if not p.is_file():continue
    assert p.stat().st_size<2*1024*1024,p
    assert not p.name.endswith(('.img','.cpio','.elf','.fw','.bin','.tar','.tar.gz','.jpg','.png')),p
    raw=p.read_bytes()
    assert (b'-----BEGIN '+b'OPENSSH PRIVATE KEY-----') not in raw,p
    assert (b'wx'+b'id_') not in raw,p
    if p.suffix=='.md':assert b'\x07' not in raw,p
subprocess.run(['python3',str(ref/'verify-evidence.py')],check=True)
items=[p for p in sorted(ref.rglob('*')) if p.is_file() and p.name!='SHA256SUMS']
(ref/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ref).as_posix()+'\n' for p in items))
subprocess.run(['python3',str(ref/'verify-evidence.py')],check=True)
for name in ('README.md','HANDOVER-NEXT.md','DOCS-INDEX.md','RX-CONSOLE.md','FLYWHEEL.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md'):
    shutil.copyfile(w/name,platform/name)
shutil.copytree(ref,platform/'reference/kernel75',dirs_exist_ok=True)
shutil.copyfile(w/'sessions/75-a640-render-and-sofef03f-clock-fix.md',platform/'sessions/75-a640-render-and-sofef03f-clock-fix.md')
shutil.copytree(w/'linux-port',platform/'linux-port',dirs_exist_ok=True,ignore=shutil.ignore_patterns('artifacts'))
tracked=subprocess.check_output(['git','-C',str(repo),'ls-files','-s'],text=True)
for line in tracked.splitlines():
    meta,name=line.split('\t',1)
    mode=meta.split()[0]
    p=repo/name
    if p.is_file() and mode in ('100644','100755'):p.chmod(0o755 if mode=='100755' else 0o644)
print('Sealed',len(items),'public evidence files; synchronized actual Git source/docs.')
