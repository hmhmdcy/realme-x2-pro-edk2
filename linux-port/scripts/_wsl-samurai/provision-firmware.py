#!/usr/bin/env python3
"""Install explicitly supplied same-handset private inputs into an offline candidate."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--root',type=Path,required=True)
p.add_argument('--firmware',type=Path,required=True,help='Own complete lib/firmware tree, including A.11 SLPI')
p.add_argument('--slpi-firmware',type=Path,required=True,help='Own A.11 SLPI MDT and complete split binaries')
p.add_argument('--ssc-source',type=Path,required=True,help='Own sdsp/, sensors-vendor/, sensors-persist/ tree')
p.add_argument('--mag-config',type=Path,required=True,help='Own validated escaped magnetometer JSON')
p.add_argument('--modem-type',type=Path,required=True,help='Own oppoVersion/modemType (expected 4)')
p.add_argument('--radio-manifest',type=Path,required=True,help='SHA256 list of same-handset modem image basenames')
a=p.parse_args();root=a.root.resolve()
if root==Path('/') or not (root/'etc/alpine-release').is_file():p.error('An offline Alpine candidate root is required')
assert not os.statvfs(root).f_flag & os.ST_RDONLY
assert a.modem_type.read_text().strip()=='4'
assert hashlib.sha256(a.mag_config.read_bytes()).hexdigest()=='9fe3391f86ef0b70b3a6b696d4d353a594bc27b5765434c7d9ede489ac6a0535','Different magnetometer config; do not bypass this model-specific check'
json.loads(a.mag_config.read_text())
for d in ['sdsp','sensors-vendor/config','sensors-persist/registry']:assert (a.ssc_source/d).is_dir(),d
assert (a.slpi_firmware/'slpi.mdt').is_file()
lines=a.radio_manifest.read_text().splitlines();assert lines
for line in lines:
 assert re.fullmatch(r'[0-9a-f]{64}  (modem\.b[0-9][0-9]|modem\.mdt|modemr\.jsn|modemuw\.jsn|wlanmdsp\.mbn)',line), 'Unsafe manifest entry'
def copy_tree(source,dest):
 source=source.resolve()
 dest.mkdir(parents=True,exist_ok=True)
 for base,dirs,files in os.walk(source,followlinks=False):
  for d in dirs:assert not (Path(base)/d).is_symlink(),'Source directory symlink'
  (dest/Path(base).relative_to(source)).mkdir(parents=True,exist_ok=True)
  for name in files:
   f=Path(base)/name;resolved=f.resolve(strict=True);assert resolved.is_relative_to(source),'Source escaped'
   assert resolved.is_file(),'Only regular firmware/config files are accepted'
   target=dest/f.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
   assert not target.is_symlink(),'Destination symlink'
   shutil.copyfile(resolved,target)
def manifest(tree,target):
 rows=[]
 for f in sorted(tree.rglob('*')):
  if f.is_file():rows.append(hashlib.sha256(f.read_bytes()).hexdigest()+'  /'+f.relative_to(root).as_posix())
 target.write_text('\n'.join(rows)+'\n');target.chmod(0o600)
data=root/'var/lib/samurai/firmware';assert not data.exists(),'Use a fresh candidate; do not overwrite provisioning'
data.mkdir(parents=True,mode=0o700)
copy_tree(a.firmware,root/'lib/firmware')
copy_tree(a.slpi_firmware,root/'lib/firmware/qcom/sm8150/realme/samurai-slpi-a11')
for subtree in ['sdsp','sensors-vendor/config','sensors-persist/registry']:
 copy_tree(a.ssc_source/subtree,data/'ssc'/subtree)
file=data/'ssc/sensors-vendor/sns_reg_config'
shutil.copyfile(a.ssc_source/'sensors-vendor/sns_reg_config',file)
shutil.copyfile(a.mag_config,data/'magnetometer.json')
shutil.copyfile(a.modem_type,data/'modemType')
manifest(data/'ssc',data/'ssc.sha256')
manifest(root/'lib/firmware',data/'firmware.sha256')
radio=root/'etc/samurai-wifi';radio.mkdir(exist_ok=True)
shutil.copyfile(a.radio_manifest,radio/'modem-sha256.txt')
(radio/'wpa-empty.conf').write_text('ctrl_interface=/run/samurai-wifi/wpa-control\n')
runtime='/var/lib/samurai/firmware/'
config={'source':runtime+'ssc','manifest':runtime+'ssc.sha256',
 'firmware_manifest':runtime+'firmware.sha256','mag_config':runtime+'magnetometer.json','modem_type':runtime+'modemType'}
f=root/'etc/samurai-ssc.json';f.write_text(json.dumps(config,indent=2)+'\n');f.chmod(0o600)
print('Private firmware provisioned into offline candidate. No block device was opened; no NV was written.')
