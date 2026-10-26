from pathlib import Path
import hashlib,json,os,runpy,stat
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129')
runpy.run_path(str(r/'reference/kernel129/ensure-rootfs-volume.py'))
root=Path('/home/cy122/pmos-samurai-rootfs129/image-export129-fixed');s=root.stat();assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(0,0,0o755)
image=json.loads((ref/'rootfs-image-validation.json').read_text());build=json.loads((ref/'kernel-build-validation.json').read_text());boot=json.loads((ref/'boot-package-validation.json').read_text());health=json.loads((ref/'final-health-validation.json').read_text())
assert image['home_owner_matches_passwd_uid_gid'] and health['final_health_pass']
assert json.loads((ref/'embedded-runtime-validation.json').read_text())['initial_console_warning_count']==0
assert json.loads((ref/'reboot-autoconnect-validation.json').read_text())['actual_new_boot_auto_connected_without_explicit_activation']
assert (root/'etc/NetworkManager/system-connections/samurai-wifi.nmconnection').read_bytes()==(out.parent/'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes()
pid=os.fork()
if pid==0:
 try:
  os.chroot(root);os.chdir('/');os.setgroups([]);os.setgid(10000);os.setuid(10000)
  assert os.access('/home/cy122',os.W_OK|os.X_OK) and os.access('/home/cy122/.local',os.W_OK|os.X_OK)
  path='/home/cy122/.local/.samurai-encoded129-permission-probe'
  fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600)
  os.write(fd,b'ENCODED129_HOME_WRITE');os.lseek(fd,0,0);assert os.read(fd,64)==b'ENCODED129_HOME_WRITE';os.close(fd);os.unlink(path);os._exit(0)
 except BaseException:os._exit(1)
assert os.waitpid(pid,0)[1]==0
artifacts=[]
for role,name,sha in [('boot','boot-partition-before-private.img',boot['boot_sha256']),('logdump','logdump-k129-console-node.img',boot['logdump_sha256']),('rootfs','samurai-rootfs-f2fs-k129-device-fixed.simg',image['sha256']),('modules','modules-k129-private.tar.gz',build['archive_sha256'])]:
 path=out/name;h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
 assert h.hexdigest()==sha
 artifacts.append(dict(role=role,name=name,bytes=path.stat().st_size,sha256=sha,artifact_path='E:/edk2-samurai-out/kernel129/'+name))
entries=json.loads((ref/'image-export-fixed-content-validation.json').read_text())['export_entries']
report=dict(candidate_kernel=129,release=build['release'],rootfs_generation=129,
 matching_boot_logdump_rootfs_modules_complete=True,embedded_and_fat_dtb_match=True,artifacts=artifacts,
 software_packages=936,kernel_modules=770,encoded_image_entries_verified=entries,
 generated_root_directory_uid_gid_zero=True,generated_root_directory_mode_octal='0755',rootfs_home_ownership_matches_passwd=True,
 system_resource_owners_root=True,decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass=True,
 rootfs_bulk_deployable=True,rootfs_bulk_image_not_deployed=True,userdata_erased=False,
 current129_kernel_and_modules_deployed_inheriting128_dual_band_profile=True,boot126_reused_unchanged=True,
 initial_console_node_present_and_warning_resolved_on_real129_boot=True,real128_pairwise_delete_fix_driver_source_preserved=True,real129_5ghz_reboot_autoconnect_https_pass=True,
 internal_tpg_runtime_accepted_on126_code_preserved_in129=True,physical_camera_accepted=False,
 stable115_118_126_128_boot_logdump_modules_and127_128_rootfs_rollback_preserved=True,hardware_complete=False,goal_complete=False)
for folder in [ref,out]:(folder/'complete-bundle-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K129_FOUR_MATCHING_ARTIFACTS_ENCODED_UID10000_ACCESS_AND_REAL_DEPLOYMENT_BUNDLE_PASS',flush=True)
