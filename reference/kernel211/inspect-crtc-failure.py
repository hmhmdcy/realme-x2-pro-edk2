from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
p=root/'k211-quiesce/explicit-crtc-disable.txt';lines=p.read_text().splitlines()
print(json.dumps(dict(selected_error=[l for l in lines if l.startswith(('Traceback','  File','AssertionError','OSError','ValueError'))],vtconsole_bound=Path('/sys/class/vtconsole/vtcon1/bind').read_text().strip(),drm_client_lines=len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines()),active_crtcs=Path('/sys/kernel/debug/dri/1/state').read_text().count('active=1'))))
