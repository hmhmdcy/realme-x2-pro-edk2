"""Only USB ko and manifest; preserve currentf6 protection and834 service."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023');OUT=BASE/'usb-irq-wake-cohort-private-01'
LEAF=ROOT/'reference/charging-oem-audit-20261023/usb-input-irq-wake-candidate'
s=importlib.util.spec_from_file_location('wake_packet_original',HERE.parent/'protection-profile-update/prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def write(path,raw):
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def main():
 assert not OUT.exists();ko=json.loads((LEAF/'ko-result.json').read_bytes());assert ko['passed'] and not ko['diagnostics'] and not ko['unresolved_strong_imports'] and ko['strong_import_count']==49
 assert all(c['terminal'] and c['returncode']==0 for c in ko['commands'])
 original=(BASE/'usb-input-pm-notify-module-private-02/samurai-usb-input-pm-notify-private.ko').read_bytes()
 module=(BASE/'usb-input-irq-wake-module-private-01/samurai-usb-input-irq-wake-private.ko').read_bytes()
 assert sha(original)=='ebfcb45d436f0f08dcaf4e400ea18b18cf3bd208863de33444e76c20faab4624' and sha(module)==ko['module_sha256']=='13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4'
 old_raw=(BASE/'protection-observed-2719-cohort-private-02/manifest-new.json').read_bytes();old=json.loads(old_raw);assert sha(old_raw)=='8c5b7be90c4d22ba3db418c7225894e155b2cf5257eda0a681da1136081cef3c'
 usb=old['modules']['samurai-usb-input']['target'];manifest='/usr/share/samurai-charging/manifest.json'
 assert old['modules']['samurai-gauge-protection']['sha256']=='f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e' and old['installed_files']['/usr/sbin/samurai-charging']=='83469a88beab16cd190793ddf65e672438d0a97aaa812b63a47b4bbb4f22472f'
 new=copy.deepcopy(old);new['modules']['samurai-usb-input']['sha256']=sha(module);new['installed_files'][usb]=sha(module);new['adapter_revision']='usb-irq-wake-01';new_raw=(json.dumps(new,indent=2)+'\n').encode()
 forward=m.packet([(usb,module),(manifest,new_raw)]);inverse=m.packet([(usb,original),(manifest,old_raw)])
 assert m.packet([(usb,module),(manifest,new_raw)])==forward
 os.umask(0o077);OUT.mkdir(mode=0o700)
 for name,raw in [('forward-two-files.tar.gz',forward),('rollback-two-files.tar.gz',inverse),('manifest-old.json',old_raw),('manifest-new.json',new_raw)]:write(OUT/name,raw)
 result=dict(passed=True,prepared_only=True,deployed=False,source_usb_sha256=sha(original),target_usb_sha256=sha(module),source_usb_note_sha256='f3c8d708a7122549a8733b5c171a2c2895e63eccaa76e31e5dfdbd9ca2ff46ae',target_usb_note_sha256=ko['module_note_sha256'],
  source_manifest_sha256=sha(old_raw),target_manifest_sha256=sha(new_raw),target_files={usb:sha(module),manifest:sha(new_raw)},source_files={usb:sha(original),manifest:sha(old_raw)},
  forward=dict(sha256=sha(forward),bytes=len(forward)),rollback=dict(sha256=sha(inverse),bytes=len(inverse)),
  retained_protection_sha256=old['modules']['samurai-gauge-protection']['sha256'],retained_protection_note_sha256='bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd',
  retained_service_sha256=old['installed_files']['/usr/sbin/samurai-charging'],retained_charger_sha256=old['modules']['samurai-mp2650']['sha256'],
  retained_boot_sha256='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06',retained_logdump_sha256='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83',
  current_Image504_and_502_config_exports_compatibility_sha256='1536496f7df88d71f39be324b7081cef0ab2b405bdec38e4095106316048e71d',
  cold_activation_required=True,hot_unload_allowed=False,Image_or_rootfs_rebuilt=False,physical_USB_wakeup_accepted=False,
  source_delivery_sha256=sha((LEAF/'delivery.json').read_bytes()),module_build_result_sha256=sha((LEAF/'ko-result.json').read_bytes()))
 for p in [HERE/'cohort-result.json',OUT/'cohort.json']:write(p,(json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({k:result[k] for k in ['passed','target_manifest_sha256','forward','rollback','deployed']}))
if __name__=='__main__':main()
