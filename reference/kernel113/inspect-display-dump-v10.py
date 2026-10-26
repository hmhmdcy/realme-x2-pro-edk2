from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'display-dump-after-v10.tar'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='518da7aa07c0220596b8ea66eefccce1a191e1ca17164f7d0b781adc78c41f82'
with tarfile.open(path) as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['dumps-found.txt'].strip()==b'1' and data['tainted.txt'].strip()==b'0'
raw=data['display-1-private.bin']
decoded=raw.decode('ascii',errors='strict')
(out/'display-v10-decoded-private.txt').write_text(decoded)
safe=[]
for line in decoded.splitlines():
    if re.match(r'\s*(enable|active|mode|crtc|connector|plane|format|rotation|crtc-pos|src-pos|self_refresh_active)=',line):
        safe.append(line.strip())
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            display_dump_sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
            kernel_display_snapshot_ascii=True,raw_snapshot_private=True,
            dpu_timeouts=data['dmesg.txt'].count(b'frame done timeout'),
            selected_drm_state=safe[:80],permanent_display_fix_accepted=False)
(ref/'display-v10-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
