from pathlib import Path
import hashlib, json, tarfile, re

private=Path('/mnt/e/edk2-samurai-out/kernel114')
archive=private/'qmi-readonly-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='d7073b5a54ae9bde74fe123ea19c93882e018f4d1f23f5686232884e020eb09e'
with tarfile.open(archive) as tar:
    files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==digest
results=dict(line.split() for line in files['results.txt'].decode().splitlines())
assert all(results[p]=='0' for p in ['dms-get-capabilities','dms-get-operating-mode','uim-get-card-status','nas-get-system-info'])
before=files['dmesg-before.txt'].decode(); after=files['dmesg-after.txt'].decode()
count=lambda s,p:len(re.findall(p,s,re.I))
report=dict(archive_sha256_verified=True,all_member_hashes_verified=True,
            query_exit_codes={k:int(v) for k,v in results.items()},modem_control_channel_verified=True,
            modemmanager_enumeration=False,cellular_data_not_verified=True,gnss_not_verified=True,
            loc_failure=files['loc-get-supported-messages-private.txt'].decode().strip(),
            nv_sources_unchanged=files['nv-check.txt'].decode().count(': OK')==6,
            other_sources_unchanged=files['source-check.txt'].decode().count(': OK')==4,
            taint_after=int(files['taint-after.txt']),
            new_dpu_timeouts=count(after,'frame done timeout')-count(before,'frame done timeout'),
            new_gpu_faults=count(after,'gpu fault')-count(before,'gpu fault'),
            goal_complete=False)
assert report['nv_sources_unchanged'] and report['other_sources_unchanged']
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/qmi-readonly-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
