"""Record one transition before submission; never resubmit after an uncertain result."""
from pathlib import Path
import base64,hashlib,importlib.util,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');marker=P/'normal-reboot-request-private.json';assert not marker.exists()
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
b=(R/'normal-reboot.py').read_bytes();compile(b,'normal-reboot.py','exec')
code=r'''
from pathlib import Path
import base64,hashlib,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k244-tools/normal-reboot.py';assert not p.exists();p.write_bytes(base64.b64decode(PAYLOAD));compile(p.read_bytes(),str(p),'exec');os.sync();print(json.dumps(dict(stage=244,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),staged=True)))
'''.replace('PAYLOAD',repr(base64.b64encode(b).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'normal-reboot-stage-private.log').write_bytes(x.stdout+x.stderr)
x=host.ssh('python3 /var/lib/samurai/k244-tools/normal-reboot.py --inspect',timeout=20);v=json.loads(x.stdout);assert v['current_boot_guard_pass'] and v['quiesce_pass'];(P/'normal-reboot-preflight-private.json').write_bytes(x.stdout)
marker.write_text(json.dumps(dict(stage=244,request_count=1,normal_linux_restart_only=True,source_sha256=hashlib.sha256(b).hexdigest(),transition_pending=True),indent=2)+'\n')
try:
 x=host.ssh('python3 /var/lib/samurai/k244-tools/normal-reboot.py',timeout=20);out=x.stdout+x.stderr
except Exception:
 p=P.parent/'kernel240/transport-last-failure-private.log';out=p.read_bytes() if p.exists() else b''
(P/'normal-reboot-submit-private.log').write_bytes(out)
print(json.dumps(dict(stage=244,single_request_recorded=True,before_restart_receipt_observed=b'before_single_normal_restart' in out,do_not_resubmit=True,fresh_boot_observation_required=True)))
