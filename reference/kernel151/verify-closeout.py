"""Read-only closeout: verify the deployed GPU fix and record current health."""
from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, time

os.umask(0o077)
base = Path('/var/lib/samurai/k151-closeout')
base.mkdir(mode=0o700, exist_ok=True)
deployment = Path('/var/lib/samurai/k149-deployment')
receipt = json.loads((deployment/'deployment.json').read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(base/'boot-id-private.txt').write_bytes(boot)
library = Path('/usr/lib/libvulkan_freedreno.so')
package_database = Path('/lib/apk/db/installed')
package_database_before = digest(package_database)
protected = {
    'installed_library_matches_deployed_fix': digest(library) == receipt['candidate_sha256'],
    'original_library_backup_verified': digest(deployment/'libvulkan_freedreno.so.original') == receipt['original_sha256'],
    'package_database_matches_stage149': package_database_before == receipt['installed_sha256'],
    'desktop_configuration_preserved': digest(Path('/etc/greetd/samurai-phosh.toml')) == receipt['samurai-phosh.toml_sha256'],
    'same_boot_as_verified_deployment': boot == (deployment/'boot-id-private.txt').read_bytes(),
}
def counts():
    log = subprocess.check_output(['dmesg'], text=True)
    return {k: log.count(v) for k, v in dict(gpu_faults='gpu fault:', warnings='WARNING:',
        dpu_timeouts='frame done timeout', dsi_errors='dsi_err_worker',
        dma_prepare='unable to prepare channel').items()}
def physical_desktop():
    result = {}
    for name in ['phoc', 'phosh']:
        found = subprocess.run(['pgrep', '-x', name], capture_output=True, text=True)
        pids = []
        for pid in found.stdout.split():
            try:
                text = (Path('/proc')/pid/'status').read_text()
                if int(re.search(r'^Uid:\s+(\d+)', text, re.M)[1]) == 10000:
                    pids.append(pid)
            except FileNotFoundError:
                pass
        result[name] = sorted(pids)
    return result
before, desktop = counts(), physical_desktop()
(base/'desktop-pids-private.json').write_text(json.dumps(desktop))
samples = []
started = time.monotonic()
for index in range(6):
    samples.append(dict(index=index, counts=counts(),
        desktop_preserved=physical_desktop() == desktop,
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot))
    if index < 5: time.sleep(4)
after = counts()
with (base/'dmesg-private.txt').open('wb') as log:
    subprocess.run(['dmesg'], stdout=log, check=True)
remoteprocs = []
for entry in sorted(Path('/sys/class/remoteproc').glob('remoteproc*')):
    try: remoteprocs.append(dict(name=(entry/'name').read_text().strip(), state=(entry/'state').read_text().strip()))
    except OSError: pass
supplies = []
for entry in sorted(Path('/sys/class/power_supply').glob('*')):
    values = {}
    for key in ['type', 'status', 'health', 'capacity', 'temp', 'voltage_now', 'current_now', 'online']:
        try: values[key] = (entry/key).read_text().strip()
        except OSError: pass
    supplies.append(dict(name=entry.name, properties=values))
network = subprocess.run(['iw', 'dev', 'wlan0', 'link'], capture_output=True, text=True)
frequency = re.search(r'freq:\s*(\d+)', network.stdout)
bluetooth = subprocess.run(['rc-service', 'bluetooth', 'status'], capture_output=True, text=True)
probe_executables = [b'/var/lib/samurai/k149-tools/vulkan-hole-probe',
    b'/var/lib/samurai/k150-research/suballocation-probe',
    b'/var/lib/samurai/k150-research/vulkan-capabilities']
active = 0
for entry in Path('/proc').glob('[0-9]*'):
    try:
        args = (entry/'cmdline').read_bytes().split(b'\0')
        if args[0] in probe_executables or any(a in [b'/tmp/k149-run-probe.py',
            b'/var/lib/samurai/k150-research/run-compat-research.py',
            b'/var/lib/samurai/k150-research/suballocation-research.py'] for a in args):
            active += 1
    except (FileNotFoundError, PermissionError): pass
instances = [p.name for p in Path('/sys/kernel/tracing/instances').iterdir()
    if p.name.startswith(('k148-', 'k149-', 'k150-'))]
previous_counts = dict(gpu_faults=3, warnings=0, dpu_timeouts=0, dsi_errors=0, dma_prepare=0)
package_records = [dict(line.split(':', 1) for line in block.splitlines()
    if len(line) > 2 and line[1] == ':') for block in package_database.read_text().split('\n\n') if block.strip()]
mesa_package = next(p for p in package_records if p.get('P') == 'mesa-vulkan-freedreno')
report = dict(recorded_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    closeout_read_only=True, gpu_loads_run=0, partitions_written=0, rebooted=False,
    deployed_state='kernel147/software132 with Mesa149 local library fix',
    source_kernel_directory_version_not_filename=True, current_uname=subprocess.check_output(['uname', '-r'], text=True).strip(),
    current_kernel_build=subprocess.check_output(['uname', '-v'], text=True).strip(),
    installed_library_sha256=digest(library), checks=protected,
    package_database_sha256=package_database_before,
    stage149_package_database_sha256=receipt['installed_sha256'],
    package_database_changed_since_stage149=not protected['package_database_matches_stage149'],
    package_database_stable_during_closeout=digest(package_database) == package_database_before,
    package_count=len(package_records), mesa_package_version=mesa_package['V'],
    package_metadata_drift_cause='not established; GPU fix file and Mesa package version verified',
    sample_count=len(samples), observed_seconds=time.monotonic()-started, samples=samples,
    counts_before=before, counts_after=after,
    new_gpu_faults_since_stage149=after['gpu_faults']-3,
    counts_match_previous_closeout=after == previous_counts,
    physical_desktop_present={name:bool(pids) for name,pids in desktop.items()},
    active_test_processes=active, remaining_gpu_test_trace_instances=len(instances),
    pending_devcoredumps=len(list(Path('/sys/class/devcoredump').glob('devcd*'))),
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    wifi_associated='Connected to ' in network.stdout,
    wifi_frequency_mhz=int(frequency[1]) if frequency else None,
    bluetooth_service_started=bluetooth.returncode == 0,
    remoteproc_states=remoteprocs, power_supply_observations=supplies,
    kernel150_compatibility_candidate_deployed=False,
    full_hardware_acceptance=False)
(base/'closeout.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
required = [value for name, value in protected.items() if name != 'package_database_matches_stage149']
assert all(required) and all(report['physical_desktop_present'].values())
assert report['package_database_stable_during_closeout'] and mesa_package['V'] == '26.2.4-r1'
assert all(s['desktop_preserved'] and s['same_boot'] and s['taint'] == 0 and s['counts'] == before for s in samples)
assert after == previous_counts and active == 0 and not instances and report['pending_devcoredumps'] == 0
