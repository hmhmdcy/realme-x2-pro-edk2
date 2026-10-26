"""Verify private checkpoint bytes; emit only aggregate hardware status."""
from pathlib import Path
import hashlib, json, re, tarfile

private = Path('/mnt/e/edk2-samurai-out/kernel112')
public = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel112')
reports = {}
def read(name, expected=None):
    path = private / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected: assert digest == expected, name
    with tarfile.open(path) as tar:
        data = {m.name.removeprefix('./'): tar.extractfile(m).read() for m in tar if m.isfile()}
    checked = 0
    for key, value in data.items():
        if not key.endswith('SHA256SUMS'): continue
        base = key[:-len('SHA256SUMS')]
        for line in value.decode().splitlines():
            sha, file = line.split('  ', 1)
            assert hashlib.sha256(data[base + file.removeprefix('./')]).hexdigest() == sha, (name, file)
            checked += 1
    reports[name] = dict(sha256=digest, nested_files_verified=checked)
    return data

def runtime(name):
    data = read(name)
    assert reports[name]['nested_files_verified'] > 10
    assert b'#112 ' in data['uname.txt']
    assert data['state.txt'].splitlines()[-1] == b'0'
    assert b'/dev/sda16 / f2fs rw' in data['mounts.txt']
    assert data['nv-check.txt'].count(b': OK') == 6
    assert data['source-check.txt'].count(b': OK') == 4
    parts = dict(line.split('  ')[::-1] for line in data['partition-check.sha256'].decode().splitlines())
    base = private.parent
    for dev, file in [('/dev/sde11', 'kernel111/boot-partition-k111.img'),
                      ('/dev/sde32', 'kernel112/logdump-k112-startup.img')]:
        assert parts[dev] == hashlib.sha256((base / file).read_bytes()).hexdigest()
    assert parts['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
    log = data['dmesg.txt'].decode()
    assert re.search(r'\[\s*0\.000000\]', log)
    reports[name].update(taint=0, full_early_log_present=True,
                        dpu_timeouts=log.count('frame done timeout'),
                        gpu_faults=log.count('*** gpu fault'),
                        nv_6_unchanged=True, stock_sources_4_unchanged=True,
                        persist_unchanged=True, boot_111_logdump_112_match=True)
    return data

recovery = runtime('clean-reboot-1.tar')
normal1 = runtime('reboot-radio-clean-1.tar')
assert recovery['boot-id-private.txt'] != normal1['boot-id-private.txt']
for name, digest in [('desktop-radio-before.tar', 'edb6c10b6761c025643800be29554b00be58724eec7c0f4865ad1d1957fd9700'),
                     ('desktop-radio-after.tar', 'ffb9e58c7cbce3231253e19a238b951e23c8227fe59368e40c1a27f6a691a169'),
                     ('desktop-ram-v4-after.tar', '15b7c4dd73343a767effd58093162dc0938fa3d95e3c3b7cdca8a6d580c4f771')]:
    data = read(name, digest)
    assert data['tainted.txt'].strip() == b'0'
    assert data['pcm-idle.txt'].strip() == b'closed\nclosed'
    assert data['amps.txt'].count(b'powered=0 muted=1') == 2
    assert data['haptics.txt'].count(b'starts=0') == 1
    assert b'Leap status' in data['clock.txt'] and b'Normal' in data['clock.txt']
    assert b'alsa_output.platform-sound.HiFi__Speaker__sink' in data['sinks.txt']
    assert b'alsa_input.platform-sound.HiFi__Mic__source' in data['sources.txt']
    reports[name]['desktop_wifi_ntp_audio_idle_haptics_pass'] = True
    reports[name].update(dpu_timeouts=data['dmesg.txt'].count(b'frame done timeout'),
                        gpu_faults=data['dmesg.txt'].count(b'*** gpu fault'), taint=0)

for name in ['sensor-ram-v1.tar', 'sensor-ram-v2.tar', 'sensor-ram-v3.tar', 'sensor-ram-v4.tar']:
    if not (private / name).exists(): continue
    data = read(name)
    assert reports[name]['nested_files_verified'] > 10
    assert data['nv-after.txt'].count(b': OK') == 6
    assert data['source-after.txt'].count(b': OK') == 4
    assert data['kernel-state-after.txt'].splitlines()[-1] == b'0'
    log = data.get('dmesg-final.txt', data.get('dmesg-after.txt', b'')).decode()
    rpc = data.get('rpcd.txt', b'').decode(errors='replace')
    query = data.get('accelerometer.txt', b'').decode(errors='replace')
    reports[name].update(taint=0, slpi_final=data['slpi-final-state.txt'].decode().strip(),
                        query_exit=data.get('query-exit.txt', b'not-run').decode().strip(),
                        daemon_exit=data.get('daemon-exit.txt', b'not-run').decode().strip(),
                        dpu_timeouts=log.count('frame done timeout'), gpu_faults=log.count('*** gpu fault'),
                        sensor_i2c_fatal='I2C_ERROR_TRANSFER_TIMEOUT' in log,
                        large_input_limit_hit='Large (>256B)' in rpc,
                        large_inputs_completed=rpc.count('large-input('),
                        ram_files_opened=rpc.count('ram-open('), ram_writes=rpc.count('ram-write('),
                        accel_unavailable="No 'accel' sensor available" in query,
                        nv_6_unchanged=True, stock_sources_4_unchanged=True)

if (private / 'reboot-radio-clean-2.tar').exists():
    normal2 = runtime('reboot-radio-clean-2.tar')
    assert normal2['boot-id-private.txt'] != normal1['boot-id-private.txt']
result = dict(checkpoints=reports, physical_first_112_unlock_and_apps_confirmed=True,
              physical_recovery_112_lock_screen_confirmed=True,
              physical_second_normal_reboot_and_ram_v4_unlock_apps_confirmed=True,
              rolling_corruption_permanently_fixed=False,
              sensors_accepted=False, goal_complete=False)
(public / 'checkpoint-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(archives_verified=len(reports), nested_files_verified=sum(x['nested_files_verified'] for x in reports.values()),
                     normal_reboot_count=1 + int((private / 'reboot-radio-clean-2.tar').exists()),
                     sensor_trials={k:v for k,v in reports.items() if k.startswith('sensor-ram')},
                     goal_complete=False)))
