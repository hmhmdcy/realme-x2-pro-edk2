from pathlib import Path
import json, re, sys

root = Path('/mnt/e/edk2-samurai-out/kernel112')
prefix = sys.argv[1]
assert re.fullmatch('[a-z0-9-]+', prefix)
for phase in ('shutdown', 'startup'):
    path = root / f'{prefix}-{phase}-read-wsl.txt'
    if not path.exists():
        print(json.dumps(dict(phase=phase, captured=False)))
        continue
    log = path.read_text(errors='replace')
    times = re.findall(r'\[\s*(\d+\.\d+)\]', log)
    summary = dict(phase=phase, captured=True, bytes=path.stat().st_size,
                   first_kernel_seconds=float(times[0]) if times else None,
                   last_kernel_seconds=float(times[-1]) if times else None,
                   efi_runtime_exception='Unable to handle paging request in EFI runtime service' in log,
                   root_readonly_shutdown='Remounting remaining filesystems read-only' in log,
                   ufs_seen='ufshcd' in log,
                   f2fs_seen='F2FS' in log,
                   root_switch='switch_root' in log or 'Switching root' in log,
                   ncm_seen='NCM' in log or 'ncm' in log,
                   kernel_warns=log.count('WARNING:'),
                   dpu_timeouts=log.count('frame done timeout'),
                   slpi_start_failure='start timed out' in log)
    print(json.dumps(summary))
