from pathlib import Path
import json, os, re, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k171-home-final')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
assert boot == Path('/var/lib/samurai/k171-runtime/boot-id-private.txt').read_bytes()

def command(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.returncode, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')

command(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
module_check=command(['sh','-c','cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k171-preflash/old132-module-tree.sha256'])
(out/'module-check-private.txt').write_text(module_check)
log = command(['dmesg'])
(out / 'dmesg-private.txt').write_text(log)
amps = {a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text()
        for a in ['1-0039', '1-003a']}
pcm = {n: Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip()
       for n, p in [('playback', 'pcm0p'), ('capture', 'pcm1c')]}
process_text = command(['ps', '-o', 'pid,comm'])
(out / 'processes-private.txt').write_text(process_text)
processes = [line.split()[-1] for line in process_text.splitlines()[1:] if line.split()]
pulse = command(['su', '-s', '/bin/sh', 'cy122', '-c',
                 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sinks; XDG_RUNTIME_DIR=/run/user/10000 pactl list short sources'])
(out / 'pulse-private.txt').write_text(pulse)
saved = json.loads(Path('/var/lib/samurai/k171-dmic0-sd1-low48/mixer-before-private.json').read_text())
restored = {}
for n, v in saved.items():
    text = command(['amixer', '-c', '0', 'cget', "name='" + n + "'"])
    restored[n] = re.search(r': values=(.*)', text)[1].strip() == v
patterns = {'warnings': 'WARNING:', 'dma_prepare': 'unable to prepare channel',
            'tx_timeout': 'TX timed out', 'queue_full': 'Message buffer unavailable',
            'resume_failed': 'NGD resume failed', 'gpu_fault': 'gpu fault:',
            'kernel_oops': 'Oops:'}
underflows = []
lines = log.splitlines()
for i, line in enumerate(lines):
    if 'underflow error on TX port' in line:
        nearby = '\n'.join(lines[max(0, i-3):i])
        underflows.append(dict(preceded_by_capture_stop='slim trigger dai=1 command=0' in nearby))
report = dict(stage=171, modules132_verified=True, nv_verified=True, kernel_build=168, kernel_version=os.uname().version,
              same_boot_as_k171_runtime=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              fault_counts={n: log.count(p) for n, p in patterns.items()},
              wcd_capture_underflow_log_count=len(underflows),
              wcd_underflow_entries_preceded_by_capture_stop=sum(x['preceded_by_capture_stop'] for x in underflows),
              wcd_capture_stop_underflow_logs_not_classified_as_fixed=True,
              desktop_present=all(n in processes for n in ['phoc', 'phosh']),
              test_pcm_processes_present=[n for n in processes if n in ['aplay', 'arecord', 'paplay', 'parecord']],
              pcm=pcm, amps=amps,
              final_amplifiers_off=all('global=00' in s and 'powered=0' in s and 'muted=1' in s and 'failed=0' in s for s in amps.values()),
              ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
              original_k171_mixer_controls_restored=restored,
              kernel168_retained_boot_and_logdump171_deployed=True,
              no_amp_gain_change_in_k171=True)
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k171-home-final-private.tar.gz', 'w:gz') as archive:
    archive.add(out, arcname=out.name)
print(json.dumps(report), flush=True)
assert report['same_boot_as_k171_runtime'] and report['kernel_version'].startswith('#168 ')
assert report['taint'] == 0 and all(v == 0 for v in report['fault_counts'].values())
assert report['desktop_present'] and not report['test_pcm_processes_present']
assert all(v == 'closed' for v in pcm.values()) and report['final_amplifiers_off'] and all(restored.values())
