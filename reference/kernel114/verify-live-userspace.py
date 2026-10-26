from pathlib import Path
import hashlib, json, tarfile, re

p=Path('/mnt/e/edk2-samurai-out/kernel114/live-userspace-private.tar.gz')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='75492f521ffbeeff38be7cb9d85f87ebe9f8900cf6c4fbaf4845be14219797e3'
with tarfile.open(p) as tar:
    files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==digest
packages=files['packages-after.txt'].decode().splitlines()
assert len(packages)==936
assert all(p in packages for p in ['calls','chatty','firefox','mobile-config-firefox','megapixels','libcamera-tools','qmi-utils','rsync','strace'])
count=lambda data,p:len(re.findall(p,data.decode(),re.I))
report=dict(archive_and_member_sha_verified=True,package_count=len(packages),mobile_apps_installed_on_phone=True,
            boot_and_userdata_not_flashed=True,desktop_files_unchanged=files['desktop-check.txt'].decode().count(': OK')==4,
            source_nv_unchanged=files['nv-check.txt'].decode().count(': OK')==6 and files['source-check.txt'].decode().count(': OK')==4,
            phosh_phoc_running=bool(files['phosh-after.txt'].strip()) and bool(files['phoc-after.txt'].strip()),
            pcm_closed=files['pcm-after.txt'].decode().strip()=='closed\nclosed',
            both_amps_idle=files['amps-after.txt'].decode().count('powered=0 muted=1')==2,
            taint_after=int(files['taint-after.txt']),sensor_power_off=files['sensor-after.txt'].decode().strip()=='offline\nvdd=0 vddio=0',
            new_dpu_timeouts=count(files['dmesg-after.txt'],'frame done timeout')-count(files['dmesg-before.txt'],'frame done timeout'),
            new_gpu_faults=count(files['dmesg-after.txt'],'gpu fault')-count(files['dmesg-before.txt'],'gpu fault'),
            applications_not_launched_for_acceptance=True,hardware_complete=False,goal_complete=False)
assert all(report[k] for k in ['desktop_files_unchanged','source_nv_unchanged','phosh_phoc_running','pcm_closed','both_amps_idle','sensor_power_off'])
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/live-userspace-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
