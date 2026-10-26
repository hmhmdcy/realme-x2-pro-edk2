from pathlib import Path
import hashlib, json, tarfile

p=Path('/mnt/e/edk2-samurai-out/kernel114/loc-readonly-private.tar.gz')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='4c13394984efe58f0c1a8eb01686a1b12471b79d3759cb764e680848899195cf'
with tarfile.open(p) as tar:
    files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==digest
codes={k:int(v) for k,v in (s.split() for s in files['results.txt'].decode().splitlines())}
assert set(codes.values())=={0}
assert files['nv-check.txt'].decode().count(': OK')==6
assert files['source-check.txt'].decode().count(': OK')==4
report=dict(archive_and_members_sha_verified=True,query_exit_codes=codes,gnss_qmi_loc_control_verified=True,
            position_fix_not_verified=True,engine_not_started=True,source_nv_unchanged=True,
            earlier_unknown_cli_option_was_not_modem_failure=True,goal_complete=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/loc-readonly-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
