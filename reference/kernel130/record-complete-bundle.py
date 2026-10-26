from pathlib import Path
import hashlib,json,os,runpy,stat
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130';prev=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel130')
runpy.run_path(str(prev/'ensure-rootfs-volume.py'))
root=Path('/home/cy122/pmos-samurai-rootfs129/image-export130-fixed');s=root.stat();assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(0,0,0o755)
image=json.loads((ref/'rootfs-image-validation.json').read_text());prior=json.loads((prev/'complete-bundle-validation.json').read_text());warm=json.loads((ref/'warmboot-validation.json').read_text());service=json.loads((ref/'service-validation.json').read_text())
assert image['home_owner_matches_passwd_uid_gid'] and image['matching_candidate_kernel']==129 and warm['standard_openrc_bluez_auto_start_pass'] and service['standard_bluez587_dbus_le_bredr_auto_start_stop_pass']
assert (root/'etc/NetworkManager/system-connections/samurai-wifi.nmconnection').read_bytes()==(out.parent/'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes()
assert (root/'etc/init.d/bluetooth').read_bytes()==(ref/'bluetooth').read_bytes() and (root/'etc/runlevels/default/bluetooth').is_symlink()
pid=os.fork()
if pid==0:
 try:
  os.chroot(root);os.chdir('/');os.setgroups([]);os.setgid(10000);os.setuid(10000)
  assert os.access('/home/cy122',os.W_OK|os.X_OK) and os.access('/home/cy122/.local',os.W_OK|os.X_OK)
  path='/home/cy122/.local/.samurai-encoded130-permission-probe'
  fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600);os.write(fd,b'ENCODED130_HOME_WRITE');os.lseek(fd,0,0);assert os.read(fd,64)==b'ENCODED130_HOME_WRITE';os.close(fd);os.unlink(path);os._exit(0)
 except BaseException:os._exit(1)
assert os.waitpid(pid,0)[1]==0
artifacts=[dict(a) for a in prior['artifacts'] if a['role']!='rootfs']
artifacts.append(dict(role='rootfs',name='samurai-rootfs-f2fs-k130-device-fixed.simg',bytes=image['sparse_bytes'],sha256=image['sha256'],artifact_path='E:/edk2-samurai-out/kernel130/samurai-rootfs-f2fs-k130-device-fixed.simg'))
for a in artifacts:
 p=Path(a['artifact_path'].replace('E:','/mnt/e'));assert p.is_file() and p.stat().st_size==a['bytes'];h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
 assert h.hexdigest()==a['sha256']
report=dict(candidate_kernel=129,release=prior['release'],rootfs_generation=130,matching_boot_logdump_rootfs_modules_complete=True,
 artifacts=artifacts,software_packages=936,kernel_modules=770,encoded_image_entries_verified=json.loads((ref/'image-export-fixed-content-validation.json').read_text())['export_entries'],
 generated_root_directory_uid_gid_zero=True,generated_root_directory_mode_octal='0755',rootfs_home_ownership_matches_passwd=True,system_resource_owners_root=True,
 decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass=True,rootfs_bulk_deployable=True,rootfs_bulk_image_not_deployed=True,userdata_erased=False,
 bluetooth_service_config_runlevel_incrementally_deployed_and_actual_warm_boot_pass=True,standard_bluez_le_bredr_auto_scan_stop_actual_hci_mgmt_pass=True,
 controller_default_off_and_full_bluez_stack_available=True,original129_kernel_modules_boot_logdump_preserved=True,real129_new_boot_autonomous5ghz_pass=True,
 uart_power_on_reassembly_error_still_open=True,stable115_118_126_128_129_sources_and_rollback_preserved=True,physical_camera_accepted=False,persistent_display_fix=False,hardware_complete=False,goal_complete=False)
for folder in [ref,out]:(folder/'complete-bundle-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K130_MATCHING129_FOUR_ARTIFACTS_ENCODED_UID10000_AND_REAL_BLUEZ_WARM_BOOT_BUNDLE_PASS',flush=True)
