from pathlib import Path
import subprocess

repo=Path('/home/cy122/edk2-samurai/repo')
platform=repo/'Platform/Realme/sm8150'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','--abbrev-ref','HEAD'],text=True).strip()=='master'
paths=[
    'DOCS-INDEX.md','FLYWHEEL.md','HANDOVER-NEXT.md','NEXT-SESSION-PROMPT.md',
    'NEXT-SESSION.md','README.md','RX-CONSOLE.md','linux-port/README.md',
    'linux-port/docs/HARDWARE-STATUS.md','linux-port/dts/sm8150-samurai.dts',
    'linux-port/patches/0009-drm-panel-samsung-sofef03f-native-display.patch',
    'linux-port/kernel73-builtins.config','FdtBlob/samurai/sm8150-realme-samurai.dtb',
    'reference/kernel73','sessions/73-native-sofef03f-dsi-dsc-display.md',
]
subprocess.run(['git','-C',str(repo),'add','--']+[str(platform/p) for p in paths],check=True)
staged=subprocess.check_output(['git','-C',str(repo),'diff','--cached','--name-only','-z']).decode().split('\0')
for name in filter(None,staged):
    assert name.startswith('Platform/Realme/sm8150/')
    assert '/artifacts/' not in name and not name.endswith(('id_ed25519','dropbear_ed25519_host_key','dropbearmulti','.img','.cpio','.elf','.fw','.tar'))
    if name.endswith('.bin'):
        assert Path(name).name in ('live60-on.bin','live60-off.bin','live90-on.bin','live90-off.bin') and '/reference/kernel73/' in name
    target=repo/name
    assert target.stat().st_size<2*1024*1024, (name,target.stat().st_size)
    private_marker=b'-----BEGIN '+b'OPENSSH PRIVATE KEY-----'
    assert private_marker not in target.read_bytes(),name
check=subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--',
    '*.md','*.py','*.sh','*.ps1','*.config','*.c','*.yaml','*.dts'],capture_output=True,text=True)
assert check.returncode==0,check.stdout[:3000]+check.stderr[:3000]
print(f'Staged {len(list(filter(None,staged)))} source/evidence files; no image, proprietary blob or private key staged.')
