"""Focused transport, CAMSS and consumer state before module testing."""
import host
code = r'''
from pathlib import Path
import json,os,subprocess
root=Path('/sys/module/qcom_camss')
print(json.dumps({
 'kernel':os.uname().release,
 'taint':Path('/proc/sys/kernel/tainted').read_text().strip(),
 'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
 'camss_refcnt':(root/'refcnt').read_text().strip(),
 'camss_holders':[p.name for p in (root/'holders').iterdir()],
 'camss_runtime':Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),
 'module_path':subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip(),
 'video_nodes':{p.name:(p/'name').read_text().strip() for p in Path('/sys/class/video4linux').iterdir()},
},indent=2))
'''
import shlex
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'current-state.json').write_bytes(q.stdout)
print(q.stdout.decode())
