from pathlib import Path
import hashlib
import shutil
import subprocess

repo=Path('/home/cy122/edk2-samurai/repo')
platform=repo/'Platform/Realme/sm8150'
w=Path('/mnt/e/RealmeX2Pro edk2')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Remove only the untracked artifact mirror created by the initial broad copy.
copied=platform/'linux-port/artifacts'
original=w/'linux-port/artifacts'
if copied.exists():
    assert copied.resolve()==Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/linux-port/artifacts')
    tracked=subprocess.check_output(['git','-C',str(repo),'ls-files','--',str(copied)],text=True)
    assert not tracked.strip()
    a={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
    b={str(p.relative_to(copied)):sha(p) for p in copied.rglob('*') if p.is_file()}
    assert a==b, 'Artifact copy contains other files; preserve it'
    shutil.rmtree(copied)
paths=[
    'DOCS-INDEX.md','FLYWHEEL.md','HANDOVER-NEXT.md','NEXT-SESSION-PROMPT.md',
    'NEXT-SESSION.md','README.md','RX-CONSOLE.md','linux-port/README.md',
    'linux-port/docs/HARDWARE-STATUS.md','linux-port/docs/USB-NCM-SSH.md',
    'linux-port/initramfs/init','linux-port/kernel72-initramfs.config',
    'linux-port/refs/dropbear-2026.94-LICENSE','linux-port/scripts/build-dropbear-usb.sh',
    'linux-port/scripts/samurai-usb.sh','linux-port/scripts/usb-tcp-transfer.ps1',
    'reference/kernel72','sessions/72-usb-ncm-and-autonomous-ssh.md',
]
subprocess.run(['git','-C',str(repo),'add','--']+[str(platform/p) for p in paths],check=True)
staged=subprocess.check_output(['git','-C',str(repo),'diff','--cached','--name-only','-z']).decode().split('\0')
for name in filter(None,staged):
    assert name.startswith('Platform/Realme/sm8150/')
    assert '/artifacts/' not in name and not name.endswith(('id_ed25519','dropbear_ed25519_host_key','dropbearmulti','.img','.cpio'))
    target=repo/name
    assert target.stat().st_size<2*1024*1024, (name,target.stat().st_size)
check=subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--',
    '*.md','*.py','*.sh','*.ps1','*.config'],capture_output=True,text=True)
assert check.returncode==0,check.stdout[:3000]+check.stderr[:3000]
print(f'Staged {len(list(filter(None,staged)))} source/evidence files; no image or private key staged.')
