"""Prepare the existing identity-gated2719 diagnostic module and service opt-in."""
from pathlib import Path
import ast,copy,difflib,gzip,hashlib,io,json,os,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'protection-observed-2719-cohort-private-01'
SOURCE=ROOT/'reference/charging-oem-audit-20261023/protection-observed-2719-profile-candidate'
MODULE=ROOT/'reference/charging-oem-audit-20261023/protection-observed-2719-profile-module-candidate'
SERVICE='/usr/sbin/samurai-charging';MANIFEST='/usr/share/samurai-charging/manifest.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def write(path,raw):
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def packet(entries):
 output=io.BytesIO()
 with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0,compresslevel=9) as compressed:
  with tarfile.open(fileobj=compressed,mode='w',format=tarfile.USTAR_FORMAT) as archive:
   for name,raw in entries:
    info=tarfile.TarInfo(name.lstrip('/'));info.size=len(raw);info.mode=0o600;info.uid=info.gid=0;info.uname=info.gname='root';info.mtime=0;archive.addfile(info,io.BytesIO(raw))
 raw=output.getvalue()
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  members=archive.getmembers();assert len(members)==len(entries)
  for entry,(name,value) in zip(members,entries):
   assert '/'+entry.name==name and entry.isfile() and entry.mode==0o600 and entry.uid==entry.gid==0 and entry.mtime==0 and not entry.pax_headers
   assert archive.extractfile(entry).read()==value
 return raw
def main():
 assert not OUT.exists();os.umask(0o077)
 identity=json.loads((MODULE/'module-identity.json').read_bytes());build=json.loads((MODULE/'ko-result.json').read_bytes())
 assert sha((MODULE/'ko-result.json').read_bytes())==identity['ko_result_sha256'] and build['passed'] and not build['diagnostics']
 assert identity['module_sha256']=='f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e' and identity['strong_import_count']==31 and identity['imports_all_from_Image502_builtin']
 delivery=(SOURCE/'delivery.json').read_bytes();assert sha(delivery)==identity['source_delivery_sha256']
 for name,digest in identity['sources'].items():assert sha((SOURCE/name).read_bytes())==digest
 tests=json.loads((SOURCE/'test-result.json').read_bytes());assert tests['passed'] and tests['actual_function_groups']==11 and tests['saved_parser_and_codec_cases']==18
 for name,digest in tests['source_files'].items():assert sha((SOURCE/name).read_bytes())==digest
 old_manifest=(BASE/'usb-input-pm-notify-cohort-private-02/manifest-new.json').read_bytes();old=json.loads(old_manifest)
 assert sha(old_manifest)=='94a659ad1fd30c4014ac335a6802ef3d279bdf908408d4b99e13867132b46b82'
 old_service=(ROOT/'reference/charging-session-20261023/r8-source-integration/rootfs-sources/usr/sbin/samurai-charging').read_bytes()
 assert sha(old_service)==old['installed_files'][SERVICE]=='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
 before="load_module(meta,'samurai-gauge-protection',['register_board=1'])"
 after="load_module(meta,'samurai-gauge-protection',['register_board=1','observed_2719_diagnostic=1'])"
 assert old_service.decode().count(before)==1;new_service=old_service.decode().replace(before,after).encode();ast.parse(new_service)
 old_ko=(BASE/'protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko').read_bytes()
 ko=(BASE/'protection-observed-2719-profile-module-private-01/samurai-gauge-protection-observed-2719-private.ko').read_bytes()
 target=identity['target'];assert sha(old_ko)==old['modules']['samurai-gauge-protection']['sha256']=='7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'
 assert sha(ko)==identity['module_sha256']
 previous=json.loads((BASE/'usb-input-pm-notify-cohort-private-02/cohort.json').read_bytes());compat=previous['shared_config_export_compatibility_504_with_502'];assert compat['passed']
 assert identity['config_sha256']==previous['shared_config_export_compatibility_504_with_502']['config_sha256'] if 'config_sha256' in compat else identity['config_sha256']=='23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
 new=copy.deepcopy(old);new['modules']['samurai-gauge-protection']['sha256']=sha(ko);new['installed_files'][target]=sha(ko);new['installed_files'][SERVICE]=sha(new_service);new['adapter_revision']='protection-observed-2719-profile-01'
 new_manifest=(json.dumps(new,indent=2)+'\n').encode()
 forward_entries=[(target,ko),(SERVICE,new_service),(MANIFEST,new_manifest)]
 inverse_entries=[(target,old_ko),(SERVICE,old_service),(MANIFEST,old_manifest)]
 forward=packet(forward_entries);inverse=packet(inverse_entries);assert packet(forward_entries)==forward
 OUT.mkdir(mode=0o700)
 for name,raw in [('forward-three-files.tar.gz',forward),('rollback-three-files.tar.gz',inverse),('manifest-old.json',old_manifest),('manifest-new.json',new_manifest),('service-old.py',old_service),('service-new.py',new_service)]:write(OUT/name,raw)
 write(HERE/'samurai-charging.py',new_service)
 write(HERE/'service-opt-in.patch',''.join(difflib.unified_diff(old_service.decode().splitlines(True),new_service.decode().splitlines(True),fromfile='a/samurai-charging',tofile='b/samurai-charging')).encode())
 result=dict(passed=True,prepared_only=True,deployed=False,source_manifest_sha256=sha(old_manifest),target_manifest_sha256=sha(new_manifest),
  source_protection_sha256=sha(old_ko),target_protection_sha256=sha(ko),source_service_sha256=sha(old_service),target_service_sha256=sha(new_service),
  source_protection_note_sha256='fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',target_protection_note_sha256=identity['module_note_sha256'],
  forward=dict(sha256=sha(forward),bytes=len(forward)),rollback=dict(sha256=sha(inverse),bytes=len(inverse)),
  target_files={name:sha(raw) for name,raw in forward_entries},source_files={name:sha(raw) for name,raw in inverse_entries},
  retained_usb_sha256=old['modules']['samurai-usb-input']['sha256'],retained_charger_sha256=old['modules']['samurai-mp2650']['sha256'],
  retained_Image504=True,retained_boot_sha256=previous['retained_boot_sha256'],retained_logdump_sha256=previous['retained_logdump_sha256'],
  existing_actual_C11_and_parser18_reused=True,existing_single_KO_build_reused=True,source_delivery_sha256=sha(delivery),module_build_sha256=sha((MODULE/'ko-result.json').read_bytes()),
  ordinary_six_command_and_Health_unchanged=True,service_change_only_explicit_load_parameter=True,parameter_readonly_default_false_in_module=True,
  cold_activation_required=True,hot_reload_or_rearm_allowed=False,new_query_started=False,physical_protocol_accepted=False,TCA_semantics_verified=False)
 for p in [OUT/'cohort.json',HERE/'cohort-result.json']:write(p,(json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({k:result[k] for k in ['passed','target_manifest_sha256','target_service_sha256','forward','rollback','deployed']}))
if __name__=='__main__':main()
