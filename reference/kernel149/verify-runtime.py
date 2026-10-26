"""Verify the deployed file, same boot and physical desktop after all probes."""
from pathlib import Path
import datetime,hashlib,json,os,re,struct,subprocess
root=Path('/var/lib/samurai')
deployment=root/'k149-deployment'
m=json.loads((deployment/'deployment.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=Path('/usr/lib/libvulkan_freedreno.so')
assert digest(target)==m['candidate_sha256']
assert digest(deployment/'libvulkan_freedreno.so.original')==m['original_sha256']
assert digest(Path('/lib/apk/db/installed'))==m['installed_sha256']
assert digest(Path('/etc/greetd/samurai-phosh.toml'))==m['samurai-phosh.toml_sha256']
header=target.read_bytes()[:64]
assert header[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',header,18)[0]==183
assert target.stat().st_uid==0 and target.stat().st_mode&0o777==0o755
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(deployment/'boot-id-private.txt').read_bytes()
before=json.loads((root/'k149-deployed-gmem-holes-pm/desktop-pids-before-private.json').read_text())
for name,pids in before.items():
    for pid in pids.split():
        assert (Path('/proc')/pid/'comm').read_text().strip()==name
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
pending=[]
for proc in Path('/proc').glob('[0-9]*'):
    try:
        args=(proc/'cmdline').read_bytes().replace(b'\x00',b' ')
        if b'/tmp/k149-run-probe.py' in args or b'/k149-tools/vulkan-hole-probe' in args:
            pending.append(proc.name)
    except (FileNotFoundError,PermissionError):pass
assert not pending
instances=[p.name for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('k149-')]
assert not instances
assert not list(Path('/sys/class/devcoredump').glob('devcd*'))
d=subprocess.check_output(['dmesg'],text=True)
counts={k:d.count(v) for k,v in dict(gpu_faults='gpu fault:',warnings='WARNING:',
    dpu_timeouts='frame done timeout',dsi_errors='dsi_err_worker',dma_prepare='unable to prepare channel').items()}
assert counts==dict(gpu_faults=3,warnings=0,dpu_timeouts=0,dsi_errors=0,dma_prepare=0)
report=dict(recorded_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    actual_kernel=147,live_rootfs='software132 with local Mesa149 library patch',
    installed_library_sha256=digest(target),original_backup_sha256=digest(deployment/'libvulkan_freedreno.so.original'),
    installed_library_elf64_aarch64=True,installed_library_root_owned_executable=True,
    package_database_preserved=True,greetd_configuration_preserved=True,
    boot_preserved=True,physical_desktop_preserved=True,taint=0,cumulative_counts=counts,
    expected_stage149_reproduction_faults=2,new_faults_after_deployment=0,
    active_probe_processes=0,remaining_probe_trace_instances=0,pending_devcoredumps=0,
    deployment_persistent=True,system_package_upgrade_can_replace_local_patch=True)
(deployment/'final-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
