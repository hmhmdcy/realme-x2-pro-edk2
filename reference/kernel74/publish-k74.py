from pathlib import Path
import subprocess

repo = Path('/home/cy122/edk2-samurai/repo')
platform = repo/'Platform/Realme/sm8150'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','--abbrev-ref','HEAD'],text=True).strip()=='master'
paths = ['DOCS-INDEX.md','FLYWHEEL.md','HANDOVER-NEXT.md','NEXT-SESSION-PROMPT.md',
    'NEXT-SESSION.md','README.md','RX-CONSOLE.md','linux-port/README.md',
    'linux-port/docs/HARDWARE-STATUS.md','linux-port/patches/0010-drm-msm-sm8150-command-boot-handoff.patch',
    'reference/kernel74','sessions/74-sm8150-display-boot-handoff.md']
subprocess.run(['git','-C',str(repo),'add','--']+[str(platform/p) for p in paths],check=True)
staged = [p for p in subprocess.check_output(['git','-C',str(repo),'diff','--cached','--name-only','-z']).decode().split('\0') if p]
for name in staged:
    assert name.startswith('Platform/Realme/sm8150/')
    assert '/artifacts/' not in name and not name.endswith(('id_ed25519','dropbear_ed25519_host_key','dropbearmulti','.img','.cpio','.elf','.fw','.tar','.bin'))
    target = repo/name
    assert target.stat().st_size<2*1024*1024, name
    assert (b'-----BEGIN '+b'OPENSSH PRIVATE KEY-----') not in target.read_bytes(), name
check = subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--',
    '*.md','*.py','*.sh','*.ps1','*.c'],capture_output=True,text=True)
assert check.returncode==0,check.stdout[:3000]+check.stderr[:3000]
print(f'Staged {len(staged)} reviewed source/evidence files; no images, proprietary blobs or private keys.')
