from pathlib import Path
import host
code=r'''
from pathlib import Path
import collections,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
old=(root/'k211-user-libcamera-system/dmesg-after-private.txt').read_bytes();now=subprocess.check_output(['dmesg'])
previous=[l for l in old.splitlines() if b'WARNING:' in l];current=[l for l in now.splitlines() if b'WARNING:' in l]
counter=collections.Counter(l.split(b'] ',1)[-1].decode(errors='replace') for l in current)
print(json.dumps(dict(taint=Path('/proc/sys/kernel/tainted').read_text().strip(),archived_warning_count=len(previous),visible_warning_count=len(current),new_warning_lines=[l.decode(errors='replace') for l in current if l not in previous],warning_categories=dict(counter),baseline_start=old.splitlines()[0].decode(errors='replace'),current_start=now.splitlines()[0].decode(errors='replace'),before_reboot_dir_exists=(root/'k212-before-reboot').exists(),quiesce_dir_exists=(root/'k212-quiesce').exists())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'warning-guard-failure-private.json').write_bytes(p.stdout);print(p.stdout.decode())
