"""Compare ROM payloads to this handset's previously captured vendor files."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242');O=P/'android-rom'
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(part,name,required=True):
 p=subprocess.run(['debugfs','-R','cat /'+name,str(O/(part+'.img'))],capture_output=True)
 exists=p.returncode==0 and b'File not found' not in p.stderr and bool(p.stdout)
 if required:assert exists, 'Required ROM member missing: '+name
 if not exists:return None
 dst=O/'selected'/part/name;assert dst.resolve().is_relative_to((O/'selected'/part).resolve())
 dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True);dst.write_bytes(p.stdout)
 return p.stdout
originals={}
for location in ['vendor-source-private','vendor-followup-source-private']:
 base=Path('/mnt/e/edk2-samurai-out/kernel238')/location
 for name,value in json.loads((base/'files-manifest-private.json').read_text()).items():originals[name]=value
comparison={}
for name in ['bin/hw/android.hardware.gnss@2.1-service-qti','lib64/libgnss.so','lib64/libloc_core.so','lib64/libloc_api_v02.so','lib64/libgps.utils.so','lib64/liblbs_core.so','lib64/libqmi_cci.so']:
 data=extract('vendor',name);comparison[name]=dict(bytes=len(data),sha256=sha(data),same_as_actual238=sha(data)==originals[name]['sha256'])
gps=extract('odm','etc/gps.conf')
actual=Path('/mnt/e/edk2-samurai-out/kernel239/odm-source-private/payload/etc/gps.conf').read_bytes()
optional={}
for name in ['etc/fstab.qcom','etc/init/hw/init.qcom.rc','etc/init/hw/init.target.rc','etc/init/android.hardware.gnss@2.1-service-qti.rc','etc/gps.conf','build.prop']:
 data=extract('vendor',name,False)
 optional[name]=dict(present=data is not None,bytes=len(data) if data is not None else None)
fstab=(O/'rom-ramdisk-selected/fstab.qcom').read_text()
data_lines=[line for line in fstab.splitlines() if line and not line.lstrip().startswith('#') and '/data' in line]
fw=json.loads((P/'resolve-firmware-private.json').read_text())['private']['manifest'];modem_comparison={}
backup=Path(json.loads((P/'android-backup-source-private.json').read_text())['modem_image'])
if shutil.which('mtype'):
 for name,entry in fw.items():
  x=subprocess.run(['mtype','-i',str(backup),'::/image/'+name],capture_output=True)
  assert x.returncode==0 and len(x.stdout)==entry['bytes']
  modem_comparison[name]=dict(bytes=len(x.stdout),same_as_original_android_modem_backup=sha(x.stdout)==entry['sha256'])
private=dict(vendor_comparison=comparison,odm_gps_sha256=sha(gps),fstab_data_lines=data_lines,optional=optional,modem_comparison=modem_comparison)
report=dict(stage=242,gnss_elf_files_compared=len(comparison),all_gnss_elf_byte_exact_to_actual238=all(x['same_as_actual238'] for x in comparison.values()),
 odm_gps_conf_byte_exact_to_actual239=gps==actual,ramdisk_userdata_data_entries=len(data_lines),
 ramdisk_data_targets_physical_userdata=any('/by-name/userdata' in line for line in data_lines),
 fstab_requests_fbe=any('fileencryption=' in line for line in data_lines),
 fstab_has_formattable_data=any('formattable' in line for line in data_lines),
 modem_files_compared_to_original_android_backup=len(modem_comparison),all_modem_files_byte_exact_to_android_backup=all(x['same_as_original_android_modem_backup'] for x in modem_comparison.values()) if modem_comparison else None,
 physical_partition_install_not_executed=True,no_phone_changes=True)
(P/'rom-comparison-private.json').write_text(json.dumps(dict(report=report,private=private),indent=2)+'\n')
(R/'rom-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
