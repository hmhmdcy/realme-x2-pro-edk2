from pathlib import Path
import tarfile,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127';out=Path('/mnt/e/edk2-samurai-out/kernel127')
with tarfile.open(out/'system-owner-private.tar') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
assert data['boot-id-private.txt'].strip()==(out.parent/'kernel126/embedded-boot-id-private.txt').read_bytes().strip()
assert data['targets-private.txt']==(out/'system-resource-owner-targets-private.txt').read_bytes()
assert data['preflight.txt'].strip()==b'ALL85_PATH_CONTENT_MODE_OWNER_PREFLIGHT_PASS'
before=[l.split(' ',2) for l in data['before-private.txt'].decode().splitlines()];after=[l.split(' ',2) for l in data['after-private.txt'].decode().splitlines()]
assert len(before)==len(after)==85 and all(a[0]=='0:0' and b[1:]==a[1:] for b,a in zip(before,after))
assert data['home-unchanged.txt'].splitlines()==[b'10000:10000 2755',b'10000:10000 2700']
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['taint.txt'].strip()==b'0' and data['phosh.txt'].strip().isdigit() and data['phoc.txt'].strip().isdigit()
report=dict(metadata_fix_live_deployed=True,kernel_unchanged=126,same126_post_firmware_boot=True,system_resource_targets=85,changed_from_nonroot=sum(b[0]!='0:0' for b in before),all_file_content_hashes_verified_before_and_after=True,all_modes_preserved=True,all_system_target_owners_now_root=True,live_home_owner_already_correct_not_written=True,nv6_source4_vendor1_unchanged=True,taint=0,desktop_processes_running=True,no_bulk_userdata_flash_or_erase=True,no_firmware_mmio_i2c_gpio_or_power_operation=True,initial_preflight_rejected_trial_files_uid10000_before_mutation=True,second_preflight_accepts_only_named_trial_paths_with_exact_hash=True,goal_complete=False)
for folder in [out,ref]:(folder/'live-system-owner-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
