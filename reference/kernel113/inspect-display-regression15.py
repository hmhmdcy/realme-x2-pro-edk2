from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'display-regression-boot15.tar'
with tarfile.open(path) as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
with tarfile.open(out/'reboot-audio-clean-15.tar') as tar:
    assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
assert data['nv-check.txt'].count(b': OK')==6 and data['source-check.txt'].count(b': OK')==4
events=[]
for line in data['dmesg-after.txt'].decode(errors='replace').splitlines():
    if re.search(r'dpu|dsi|sofef',line,re.I) and re.search(r'timeout|error|failed|DSC.*power mode',line,re.I):
        safe=re.sub(r'\b[0-9a-fA-F]{8,16}\b','<hex>',line)
        events.append(safe)
snapshots=[]
for index in range(1,int(data['dumps-found.txt'])+1):
    raw=data[f'display-{index}-private.bin'];decoded=raw.decode('ascii',errors='strict')
    (out/f'display-regression15-{index}-decoded-private.txt').write_text(decoded)
    state=[line.strip() for line in decoded.splitlines() if re.match(r'\s*(enable|active|mode|format|rotation|crtc-pos|src-pos|self_refresh_active)=',line)]
    snapshots.append(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),read_exit=int(data[f'read-{index}-exit.txt']),selected_drm_state=state[:60]))
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),boot_checkpoint='reboot-audio-clean-15',
    physical_flashing_corruption_reported=True,physical_trigger_pending=True,
    startup_dpu_timeouts=json.loads((ref/'reboot-audio-clean-15-validation.json').read_text())['dpu_timeouts'],
    current_dpu_timeouts=data['dmesg-after.txt'].count(b'frame done timeout'),gpu_faults=data['dmesg-after.txt'].count(b'*** gpu fault'),
    taint_before=int(data['state-before.txt'].splitlines()[-1]),taint_after=int(data['state-after.txt'].splitlines()[-1]),
    slpi_before=data['slpi-before.txt'].decode().strip(),slpi_after=data['slpi-after.txt'].decode().strip(),
    power_before=data['power-before.txt'].decode().strip(),power_after=data['power-after.txt'].decode().strip(),
    existing_dpu_dumps_preserved=snapshots,kernel_display_events=events,nv6_sources4_unchanged=True,
    raw_logs_and_snapshots_private=True,permanent_display_fix_accepted=False,goal_complete=False)
(ref/'display-regression15-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
