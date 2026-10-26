from pathlib import Path
import json,hashlib,runpy,stat,shutil
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122');out=Path('/mnt/e/edk2-samurai-out/kernel122')
image=json.loads((ref/'rootfs-image-validation.json').read_text());assert image['encoded_image_full_directory_export_and_content_metadata_check_pass']
stage=Path('/home/cy122/pmos-samurai-rootfs122');rootstat=(stage/'image-export-fixed').stat();assert stat.S_IMODE(rootstat.st_mode)==0o755 and rootstat.st_uid==rootstat.st_gid==0
health=(out/'runtime-health-final-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert '#118 ' in health[0] and health[1:8]==['0','3492','3190','2','1','closed','closed']
assert sum(': OK' in line for line in health)==11 and sum('powered=0 muted=1' in line for line in health)==2 and 'vdd=0 vddio=0' in health and 'offline' in health
(ref/'runtime-health-validation.json').write_text(json.dumps(dict(current_kernel=118,same_boot_guard_pass=True,taint=0,phosh_phoc_original_pids_alive=True,dpu_timeouts=2,gpu_faults=1,pcm_closed_amps_idle=True,slpi_offline_power_zero=True,nv6_source4_vendor1_hash_pass=True,no_phone_mutations_this_phase=True,goal_complete=False),indent=2)+'\n')
paths=[('boot',out/'boot-partition-k121-uefi-reused.img'),('logdump',out/'logdump-k121-camera-basis.img'),('rootfs',out/'samurai-rootfs-f2fs-k121-device-fixed.simg'),('modules',out.parent/'kernel121/modules-k121-private.tar.gz')]
artifacts=[]
for role,p in paths:
    if role=='rootfs':digest=image['sha256'];assert p.stat().st_size==image['sparse_bytes']
    else:digest=hashlib.sha256(p.read_bytes()).hexdigest()
    artifacts.append(dict(role=role,private_windows_path=str(p).replace('/mnt/e/','E:/'),bytes=p.stat().st_size,sha256=digest))
assert artifacts[0]['sha256']=='e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f'
assert artifacts[1]['sha256']=='6b734cc06090c6c33a6a795045c67f083f9ba1a2f500e4f37ff52ea8840611c2'
assert artifacts[3]['sha256']=='a0d778b79be5f453fb65d0d906e6d23b45197415346be0a56f16920e21971484'
bundle=dict(candidate_kernel=121,rootfs_generation=122,matching_boot_logdump_rootfs_modules_complete=True,artifacts=artifacts,software_packages=936,kernel_modules=770,encoded_image_entries_verified=21134,generated_root_directory_mode_octal='0755',generated_root_directory_uid_gid_zero=True,no_assumption_of118_module_compatibility=True,not_deployed=True,userdata_bulk_flash_or_erase_not_performed=True,hardware_complete=False,goal_complete=False)
for folder in [out,ref]:(folder/'complete-bundle-validation.json').write_text(json.dumps(bundle,indent=2)+'\n')
boot=json.loads((ref/'boot-package-validation.json').read_text());boot['matching_full_rootfs_still_building']=False;boot['matching_full_rootfs_complete']=True;(ref/'boot-package-validation.json').write_text(json.dumps(boot,indent=2)+'\n')
cleanup=json.loads((ref/'obsolete-artifact-cleanup-validation.json').read_text());cleanup['c_free_later_recheck_bytes']=shutil.disk_usage('/mnt/c').free;cleanup['delayed_host_reclaim_observed']=cleanup['c_free_later_recheck_bytes']>cleanup['c_free_after_bytes'];(ref/'obsolete-artifact-cleanup-validation.json').write_text(json.dumps(cleanup,indent=2)+'\n')
print(json.dumps(dict(matching_bundle_complete=True,rootfs_sha256=image['sha256'],phone_still118=True,c_free_later_recheck_bytes=cleanup['c_free_later_recheck_bytes'],goal_complete=False)))
