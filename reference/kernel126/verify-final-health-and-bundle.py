from pathlib import Path
import tarfile,json,hashlib,re,stat,runpy
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126')
with tarfile.open(out/'final-health-private.tar.gz') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
assert data['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
assert data['taint.txt'].strip()==b'0' and data['sensor.txt'].strip()==b'offline\nvdd=0 vddio=0' and data['radio-audio.txt'].strip()==b'running\nrunning'
assert data['phosh.txt'].strip().isdigit() and data['phoc.txt'].strip().isdigit() and data['connector.txt'].strip()==b'connected'
assert data['dma-trace.txt'].strip()==b'N' and data['amps.txt'].count(b'failed=0')==2
samples=data['samples.txt'].decode().splitlines();assert len(samples)==6;duration=float(samples[-1].split()[1])-float(samples[0].split()[1]);assert duration>=50
before=data['dmesg-before.txt'];after=data['dmesg-after.txt'];assert after.startswith(before);new=after[len(before):].decode()
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['modules-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['modules-check.txt']
parts={n:h for h,n in (l.split('  ',1) for l in data['partitions.sha256'].decode().splitlines())};package=json.loads((ref/'firmware-deployment-package-validation.json').read_text())
assert parts['/dev/sde11']==package['boot_sha256'] and parts['/dev/sde32']==package['logdump_sha256'] and parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
warnings=['frame done timeout','*** gpu fault','Unhandled context fault','WARNING:','BUG:','Oops:'];counts={w:new.count(w) for w in warnings}
assert all(v==0 for v in counts.values())
log=after.decode();report=dict(final_health_pass=True,current_kernel=126,embedded126_dtb_prior_verified=True,same_post_firmware_boot=True,desktop_phosh_phoc_running=True,display_connected=True,drm_active_crtc_count=data['drm-state.txt'].count(b'active=1'),samples=6,sample_duration_seconds=duration,new_fault_counts=counts,total_dpu_timeouts=log.count('frame done timeout'),total_gpu_faults=log.count('*** gpu fault'),taint=0,mpss_adsp_running=True,bluetooth_hci_present=True,wlan_operstate=data['wlan.txt'].decode().strip(),pcm_closed=data['pcm.txt'].strip()==b'closed\nclosed',amps_idle=data['amps.txt'].count(b'powered=0 muted=1')==2,amps_failure_count_zero=True,slpi_and_sensor_power_off=True,debug_traces_saved_then_disabled=True,dma_trace_disabled=True,source11_and_modules770_verified=True,boot_logdump_persist_matches=True,full_hardware_long_stability_not_claimed=True,goal_complete=False)
(ref/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
runpy.run_path(str(ref/'ensure-build-volume.py'))
root=Path('/home/cy122/pmos-samurai-build126/image-export-fixed');s=root.stat();assert s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o755
ownership=json.loads((out/'rootfs-ownership-audit-private.json').read_text());assert ownership['selected']['etc']['uid']==0 and ownership['selected']['etc/passwd']['uid']==0
assert all(e['uid']==0 for e in ownership['privileged'] if e['path'].startswith('usr/'))
artifacts=[]
for role,name,expected in [('boot','boot-partition-k126-embedded-tpg.img',package['boot_sha256']),('logdump','logdump-k126-internal-tpg.img',package['logdump_sha256']),('rootfs','samurai-rootfs-f2fs-k126-device-fixed.simg',json.loads((ref/'rootfs-image-validation.json').read_text())['sha256']),('modules','modules-k126-private.tar.gz',json.loads((ref/'kernel-build-validation.json').read_text())['archive_sha256'])]:
 p=out/name;h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
 assert h.hexdigest()==expected,(role,expected,h.hexdigest())
 artifacts.append(dict(role=role,name=name,bytes=p.stat().st_size,sha256=expected))
bundle=dict(candidate_kernel=126,release='7.3.0-rc6-rmx1931-samurai-k126+',rootfs_generation=126,matching_boot_logdump_rootfs_modules_complete=True,embedded_and_fat_dtb_match=True,artifacts=artifacts,software_packages=936,kernel_modules=770,encoded_image_entries_verified=21130,generated_root_directory_mode_octal='0755',generated_root_directory_uid_gid_zero=True,privileged_usr_binaries_root_owned=True,boot_logdump_and_incremental_modules_deployed=True,rootfs_bulk_image_not_deployed=True,userdata_erased=False,internal_csid0_vfe0_tpg_accepted=True,physical_camera_accepted=False,hardware_complete=False,stable115_118_rollback_preserved=True,goal_complete=False)
for directory in [ref,out]:(directory/'complete-bundle-validation.json').write_text(json.dumps(bundle,indent=2)+'\n')
print('K126_COHERENT_EMBEDDED_DTB_BOOT_LOGDUMP_ROOTFS_MODULES_BUNDLE_VALIDATED')
