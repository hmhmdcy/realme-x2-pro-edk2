from pathlib import Path
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel139'
out = Path('/mnt/e/edk2-samurai-out/kernel139')
with tarfile.open(out / 'first-health-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out / 'embedded-boot-id-private.txt').read_bytes()
report = json.loads(data['health-validation.json'])
assert report['stage'] == 139 and report['current_kernel'] == 139
assert report['same_boot'] and report['taint_values'] == [0] and report['counters_unchanged']
assert report['phosh_present_final'] and report['phoc_present_final'] and report['desktop_pids_unchanged']
d = data['dmesg-final-private.txt'].decode()
times = [float(re.match(r'\[\s*([0-9.]+)\]', line).group(1)) for line in d.splitlines() if 'unable to prepare channel' in line]
report.update(archive_hash_verified=True, startup_tx_dma_failures=len(times),
              first_tx_dma_failure_s=times[0], last_tx_dma_failure_s=times[-1],
              message_buffer_unavailable_count=d.count('Message buffer unavailable'),
              tx_timeout_count=d.count('TX timed out'),
              later_codec_probe_after_last_failure=any('WCD934X Minor' in line and float(re.match(r'\[\s*([0-9.]+)\]', line).group(1)) > times[-1] for line in d.splitlines()),
              live_dma_prepare_root_cause_proven=False, host_unwind_fix_accepted=True,
              no_gpu_workload_since136=True, display_gpu_charge_goals_complete=False)
(ref / 'first-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
runtime = json.loads((ref / 'first-runtime-validation.json').read_text())
runtime['gpu_probe_allowed'] = False
runtime['initial_desktop_snapshot_precedes_autonomous_startup'] = True
runtime['current_dma_errors_require_investigation'] = True
runtime['final_health_record'] = 'first-health-validation.json'
(ref / 'first-runtime-validation.json').write_text(json.dumps(runtime, indent=2) + '\n')
names = ['100 prep failures do not exhaust slots', 'TIDs and PM references balanced',
         'success and payload after failure sequence', 'full ring preserves earlier slots and frees own TID',
         'core TID allocation failure releases PM', 'converted user TID failure reserves no slot',
         'converted user prep failure frees TID and PM', 'TX-only prep failure has no spurious TID free',
         'earlier inflight descriptor remains valid', 'direct user caller retains TID error ownership',
         'early controller-state failure initializes TID', 'unsupported destination unwinds allocated core TID']
host = json.loads((ref / 'host-fault-injection-validation.json').read_text())
host['case_names'] = names
host['related_pm_fix_discussion'] = 'https://lkml.iu.edu/2609.2/04989.html'
(ref / 'host-fault-injection-validation.json').write_text(json.dumps(host, indent=2) + '\n')
print(json.dumps(report, indent=2))
