from pathlib import Path
import hashlib,json,math,re,statistics,sys,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
trial=sys.argv[1] if len(sys.argv)>1 else 'v13'
assert trial in ('v13','v14','v15','v16')
checkpoint={'v13':'reboot-audio-clean-9','v14':'reboot-audio-clean-10','v15':'reboot-audio-clean-11','v16':'reboot-audio-clean-12'}[trial]
firmware='c35' if trial=='v16' else 'c28'
rotation_reported='--physical-rotation-completed' in sys.argv[2:]
window_confirmed='--rotation-window-confirmed' in sys.argv[2:]
assert not rotation_reported or trial in ('v14','v15')
assert not window_confirmed or (rotation_reported and trial=='v15')
assert all(arg in ('--physical-rotation-completed','--rotation-window-confirmed') for arg in sys.argv[2:])
receipt=None
if window_confirmed:
    receipt_path=out/'rotation-v15-user-receipt-private.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    assert receipt['trial']==trial and receipt['user_completed_rotation']
    assert receipt['sampling_still_active_at_reply'] and 0<=receipt['window_elapsed_seconds']<175
    assert receipt['samples_at_reply']>0
path=out/f'sensor-ram-{trial}.tar'
with tarfile.open(path) as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
with tarfile.open(out/(checkpoint+'.tar')) as tar:
    assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
assert data['magnetometer-exit.txt'].strip()==b'0'
log=data['magnetometer.txt'].decode()
names=re.findall(r'^.*  name: ([^\r\n]+)',log,re.M)
vendors=re.findall(r'^.*  vendor: ([^\r\n]+)',log,re.M)
assert names and vendors
samples=[tuple(map(float,m)) for m in re.findall(r'^Magnetometer sensor measurement: X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+) μT$',log,re.M)]
assert len(samples)>=20 and len(set(samples))>=20
assert all(math.isfinite(value) and abs(value)<2000 for sample in samples for value in sample)
norms=[math.sqrt(sum(value*value for value in sample)) for sample in samples]
assert all(norm>0 for norm in norms)
directions=[tuple(value/norm for value in sample) for sample,norm in zip(samples,norms)]
max_angle=max(math.degrees(math.acos(max(-1.0,min(1.0,sum(x*y for x,y in zip(a,b))))))
              for i,a in enumerate(directions) for b in directions[i+1:])
rotation_response=rotation_reported and window_confirmed and len(samples)>=200 and max_angle>=30.0
assert 'Sensor disable request sent successfully' in log
assert data['firmware-selected.txt'].strip()==f'qcom/sm8150/realme/samurai-{firmware}-trial/slpi.mdt'.encode()
assert data['firmware-final.txt']==data['firmware-before.txt']
assert data['slpi-final-state.txt'].strip()==b'offline'
assert data['power-final.txt'].strip()==b'vdd=0 vddio=0'
assert data['kernel-state-after.txt'].splitlines()[-1]==b'0'
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    kernel_build=113,boot_checkpoint=checkpoint,firmware_reference=('rmx1931-global-c35-00098' if firmware=='c35' else 'rmx1931-chinese-c28-00098'),
    sensor_names=sorted(set(names)),vendors=sorted(set(vendors)),sample_count=len(samples),
    unique_vectors=len(set(samples)),finite_microtesla_vectors=True,
    streaming_received=True,disable_confirmed=True,
    matrix_all_zero_warning='Mount matrix provided by firmware is all 0' in log,
    physical_rotation_completed_by_user=rotation_reported,
    physical_rotation_within_sampling_window_confirmed=window_confirmed,
    response_received_while_sample_count=(receipt['samples_at_reply'] if receipt else None),
    response_window_elapsed_seconds=(receipt['window_elapsed_seconds'] if receipt else None),
    maximum_vector_direction_separation_degrees=round(max_angle,1),
    physical_rotation_response_verified=rotation_response,
    rotation_response_gate={'minimum_samples':200,'minimum_direction_separation_degrees':30},
    calibration_or_compass_accuracy_accepted=False,
    original_firmware_selector_restored=True,slpi_offline_and_sensor_power_off=True,
    all_sensors_accepted=False,goal_complete=False)
(ref/f'magnetometer-{trial}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/f'magnetometer-{trial}-vectors-private.json').write_text(json.dumps(samples)+'\n')
print(json.dumps(report))
