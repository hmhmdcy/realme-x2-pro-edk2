from pathlib import Path
import json,os,subprocess

out=Path('/mnt/e/edk2-samurai-out/kernel203');out.mkdir(mode=0o700,exist_ok=True)
root=Path('/home/cy122/pmos-samurai-rootfs01')
report={}
for relative in ['work/config_abuild','work/pmbootstrap.cfg']:
 p=root/relative
 if p.is_file():(out/(p.name+'-private.txt')).write_bytes(p.read_bytes())
report['rootfs_top_entries']=sorted(p.name for p in root.iterdir())
report['work_top_entries']=sorted(p.name for p in (root/'work').iterdir())
report['pmaports_device_categories']=sorted(p.name for p in (root/'pmaports/device').iterdir() if p.is_dir())
report['host_tools']={name:subprocess.run(['sh','-c','command -v '+name],capture_output=True,text=True).stdout.strip() for name in ['pmbootstrap','abuild','apk','qemu-aarch64-static','openssl']}
matches=[]
for category in (root/'pmaports/device').iterdir():
 if category.is_dir():matches.extend(str(p.relative_to(root/'pmaports')) for p in category.iterdir() if 'samurai' in p.name or 'rmx1931' in p.name)
report['owned_device_package_matches']=matches
(out/'build-environment-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
