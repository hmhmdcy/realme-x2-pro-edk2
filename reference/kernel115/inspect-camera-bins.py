from pathlib import Path
import tarfile,hashlib,json,subprocess,struct,re
out=Path('/mnt/e/edk2-samurai-out/kernel115');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
archive=out/'vendor-camera-bins-v3-private.tar.gz'
with tarfile.open(archive) as tf:
    data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for row in data['SHA256SUMS'].decode().splitlines():
    digest,name=row.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['vendor-after-check.txt'].strip()==b'/dev/sda9: OK'
assert data['nv-check.txt'].count(b': OK')==6
assert ' ro,' in data['mount-options.txt'].decode() and 'norecovery' in data['mount-options.txt'].decode()
folder=out/'vendor-camera-bins';folder.mkdir(exist_ok=False);records=[]
for name,blob in data.items():
    if not name.startswith('modules/'): continue
    assert '/' not in name.removeprefix('modules/')
    assert blob.startswith(b'QTI Chromatix Header')
    dest=folder/Path(name).name;dest.write_bytes(blob)
    strings=subprocess.check_output(['strings','-a','-t','x',str(dest)],text=True)
    (folder/(dest.name+'.strings-private.txt')).write_text(strings)
    assert struct.pack('<I',len(blob)) in blob[:40]
    records.append(dict(name=dest.name,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),qti_header=True,
        declared_size_offset=blob[:40].find(struct.pack('<I',len(blob))),parser_version='1.3.2' if b'Parameter Parser V1.3.2' in blob[:100] else 'unknown',
        identity_candidates=[l.strip() for l in strings.splitlines() if any(s in l.lower() for s in ['imx','s5k','ov02','sunny','qtech','sensor'])]))
(out/'camera-binary-analysis-private.json').write_text(json.dumps(records,indent=2)+'\n')
report=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),all_member_hashes_verified=True,vendor_readonly_noload=True,
 vendor_partition_unchanged=True,nv6_preserved=True,sensor_configuration_bins=records,
 register_power_sequence_parser_pending=True,physical_camera_accepted=False,goal_complete=False)
for r in report['sensor_configuration_bins']: r.pop('identity_candidates')
(ref/'camera-bin-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
