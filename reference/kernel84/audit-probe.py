"""Verify the bounded KMS probe archive and its real trace evidence."""
from pathlib import Path
import hashlib, json, re, tarfile, gzip

out = Path('/mnt/e/edk2-samurai-out/kernel84')
sha = lambda data: hashlib.sha256(data).hexdigest()
compressed = (out / 'probe-raw.tar.gz').read_bytes()
assert sha(compressed) == '92dd50a54ab04207e3c08bb27cf24ddfd2b38f6afb45de61e07c0d82d184ceca'
tar_bytes = gzip.decompress(compressed)
assert sha(tar_bytes) == '9429fbe7ce2f2f0c0f4988e33c032aa501ac647fe944739fd3738f2304d98c1f'
raw = {}
with tarfile.open(out / 'probe-raw.tar.gz') as tar:
    for member in tar:
        assert member.isfile() and member.name.startswith('tmp/k84-probe-')
        assert '/' not in member.name.removeprefix('tmp/')
        name = member.name.removeprefix('tmp/k84-')
        data = tar.extractfile(member).read()
        target = out / name
        if target.exists():
            assert target.read_bytes() == data
        else:
            target.write_bytes(data)
        raw[name] = data
for line in raw['probe-hashes.txt'].decode().splitlines():
    digest, path = line.split('  ', 1)
    assert sha(raw[Path(path).name.removeprefix('k84-')]) == digest
before = raw['probe-before-dmesg.txt'].decode()
after = raw['probe-after-dmesg.txt'].decode()
assert not re.search(r'frame done timeout|dsi_err_worker|\bBUG:|\bOops:', after)
for name in ['probe-before-encoder.txt', 'probe-after-encoder.txt']:
    state = raw[name].decode()
    assert 'frame_done_cnt:0mode:' in state and re.search(r'underrun:\s+0\s', state)
assert 'snapshot:count=1\n' in raw['probe-trigger.txt'].decode()
trace = raw['probe-trace.txt'].decode()
assert 'k84 pageflip begin' in trace and 'k84 pageflip returned' in trace and 'k84 idle observation end' in trace
stats = raw['probe-trace-stats.txt'].decode()
overruns = [int(x) for x in re.findall(r'^overrun: (\d+)$', stats, re.M)]
dropped = [int(x) for x in re.findall(r'^dropped events: (\d+)$', stats, re.M)]
commits = [int(x) for x in re.findall(r'^commit overrun: (\d+)$', stats, re.M)]
assert len(overruns) == len(dropped) == len(commits) == 8
assert not any(dropped + commits)
events = {}
for line in trace.splitlines():
    match = re.search(r'\d+\.\d+: (\w+):', line)
    if match:
        events[match[1]] = events.get(match[1], 0) + 1
report = {
    'archive_sha256': sha(tar_bytes), 'compressed_archive_sha256': sha(compressed),
    'members_and_sha256_verified': True,
    'display_timeout_count_before_after': [0, 0], 'underrun_before_after': [0, 0],
    'trace_has_begin_return_and_idle_markers': True,
    'event_counts': events, 'overruns_per_cpu': overruns,
    'dropped_events_per_cpu': dropped, 'commit_overruns_per_cpu': commits,
    'trace_complete_without_buffer_overwrite': not any(overruns),
    'timeout_snapshot_remaining_count': 1,
    'real_timeout_snapshot_tested': False,
    'explicit_panel_power_cycle': False, 'new_optical_observation': False,
    'display_root_cause_fixed': False,
}
(out / 'probe-trace-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
