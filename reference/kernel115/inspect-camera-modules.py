from pathlib import Path
import tarfile,hashlib,json,subprocess,re
out=Path('/mnt/e/edk2-samurai-out/kernel115')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
archive=out/'vendor-camera-source-private.tar.gz'
with tarfile.open(archive) as tf:
    data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for row in data['SHA256SUMS'].decode().splitlines():
    digest,name=row.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['vendor-after-check.txt'].strip()==b'/dev/sda9: OK'
assert data['nv-check.txt'].count(b': OK')==6
options=data['mount-options.txt'].decode().split()[3].split(',')
assert 'ro' in options and ('noload' in options or 'norecovery' in options)
folder=out/'vendor-camera-modules';folder.mkdir(exist_ok=False)
records=[]
for name,blob in data.items():
    if not name.startswith('modules/'): continue
    assert '/' not in name.removeprefix('modules/') and blob[:4]==b'\x7fELF'
    dest=folder/Path(name).name;dest.write_bytes(blob)
    elf=subprocess.check_output(['aarch64-linux-gnu-readelf','-aW',str(dest)],text=True)
    dis=subprocess.check_output(['aarch64-linux-gnu-objdump','-d',str(dest)],text=True)
    strings=subprocess.check_output(['strings','-a',str(dest)],text=True)
    (folder/(dest.name+'.readelf-private.txt')).write_text(elf)
    (folder/(dest.name+'.disasm-private.txt')).write_text(dis)
    (folder/(dest.name+'.strings-private.txt')).write_text(strings)
    records.append(dict(name=dest.name,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),exported_symbols=[l.split()[-1] for l in elf.splitlines() if 'GLOBAL' in l and 'DEFAULT' in l and ' UND ' not in l],descriptor_strings=[l for l in strings.splitlines() if any(n in l.lower() for n in ['sensor','1920','ov02','s5k','imx'])]))
(out/'camera-module-analysis-private.json').write_text(json.dumps(records,indent=2)+'\n')
report=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),all_member_hashes_verified=True,vendor_readonly_noload=True,vendor_partition_unchanged=True,nv6_preserved=True,same_handset_module_names=[r['name'] for r in records],modules=5,physical_sensor_detection_not_done=True,goal_complete=False)
(ref/'camera-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
for r in records: print(r['name'],r['exported_symbols'])
