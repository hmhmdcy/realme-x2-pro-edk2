"""Verify the complete first-boot archive, configuration and trace trigger."""
from pathlib import Path
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel84')
sha = lambda data: hashlib.sha256(data).hexdigest()
archive = out / 'ready-raw-complete.tar'
assert sha(archive.read_bytes()) == '93f10bf041ebf24603e8f31be8e54732eb183960457d6d43126e4470cf9a59d4'
raw = {}
with tarfile.open(archive) as tar:
    for member in tar:
        assert member.isfile() and member.name.startswith('tmp/k84-ready-')
        assert '/' not in member.name.removeprefix('tmp/')
        name = member.name.removeprefix('tmp/k84-')
        data = tar.extractfile(member).read()
        target = out / name
        if target.exists():
            assert target.read_bytes() == data
        else:
            target.write_bytes(data)
        raw[name] = data
for line in raw['ready-hashes.txt'].decode().splitlines():
    digest, path = line.split('  ', 1)
    assert sha(raw[Path(path).name.removeprefix('k84-')]) == digest
assert raw['ready-config.txt'] == (out / 'config-ready').read_bytes()
config = raw['ready-config.txt'].decode()
for symbol in ['HIST_TRIGGERS', 'TRACER_SNAPSHOT', 'BOOTTIME_TRACING', 'BOOT_CONFIG_EMBED', 'BOOT_CONFIG_FORCE']:
    assert f'CONFIG_{symbol}=y\n' in config
assert '# CONFIG_FUNCTION_TRACER is not set' in config
state = raw['ready-state.txt'].decode()
assert state.startswith('f02d218a-cc7d-4b92-8858-c8eeaeab5777\n')
assert '#85 SMP PREEMPT' in state and state.splitlines()[3] == '0'
assert 'frame_done_cnt:0mode:' in state
log = raw['ready-dmesg.txt'].decode()
assert not re.search(r'trace_boot: Failed|frame done timeout|dsi_err_worker|\bBUG:|\bOops:', log)
settings = raw['ready-trace-settings.txt'].decode().splitlines()
assert settings[0] == 'nop' and '[mono]' in settings[1]
assert settings[2] == '513' and settings[3] == '1' and settings[4] == 'snapshot:count=1'
assert any(x.startswith('dpu:') for x in settings[5:])
assert any(x.startswith('drm:') for x in settings[5:])
assert any(x.startswith('drm_msm_atomic:') for x in settings[5:])
hashes = raw['ready-partition-hashes.txt'].decode()
assert hashes.startswith('08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405  -\n')
assert '60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b  /dev/sde32' in hashes
stats = raw['ready-trace-stats.txt'].decode()
overruns = [int(x) for x in re.findall(r'^overrun: (\d+)$', stats, re.M)]
dropped = [int(x) for x in re.findall(r'^dropped events: (\d+)$', stats, re.M)]
trace = raw['ready-trace.txt'].decode()
report = {
    'archive_sha256': sha(archive.read_bytes()),
    'archive_members_and_hashes_verified': True,
    'running_config_byte_identical': True,
    'boot_id': state.splitlines()[0],
    'uptime_seconds': float(state.splitlines()[2].split()[0]),
    'kernel_build': 85, 'taint': 0,
    'boot_partition_prefix_unchanged': True, 'logdump_verified': True,
    'trace_boot_errors': 0, 'snapshot_action_installed': True,
    'tracer': 'nop', 'clock': 'mono', 'buffer_actual_kib_per_cpu': 513,
    'enabled_event_count': len(settings[5:]),
    'timeout_count': 0, 'underrun_count': 0,
    'overruns_per_cpu': overruns, 'dropped_events_per_cpu': dropped,
    'trace_event_lines': len([x for x in trace.splitlines() if x and not x.startswith('#')]),
    'snapshot_trigger_exercised_by_real_timeout': False,
    'display_root_cause_fixed': False,
    'gauge_charger_configuration_written': False,
}
(out / 'ready-live-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
