"""Prepare an independent, unprocessed IMX319 exposure reference on #298."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel291/samurai-physical-raw.c').read_text().replace('k290','k298').replace('#290 ','#298 ')
p=HERE/'samurai-raw.c';assert not p.exists();p.write_text(s)
binary=host.PRIVATE/'physical-raw-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'raw-probe-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--capture','/tmp/not-used'],capture_output=True).returncode==3
for name in ['native-raw.py','launch-raw.py','poll-raw.py']:
 s=(HERE.parent/'kernel291'/name).read_text().replace('291','298').replace('290','298')
 if name=='native-raw.py':
  s=s.replace('raw_reference=True,','raw_reference=True,dark_scene_confirmed=False,no_dark_calibration_claimed=True,')
 if name=='poll-raw.py':
  s=s.replace('print(json.dumps(report,indent=2))',"print(json.dumps(dict(state=report['state'],failure=report['failure'],summary=None if report['summary'] is None else {k:report['summary'][k] for k in ['tool_exit','actual_frames','passed','graph_restored','fault_delta']}),indent=2))")
 (HERE/name).write_text(s)
(HERE/'raw-tool-validation.json').write_text(json.dumps(dict(stage=298,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,not_run_on_phone=True,exposure_codes=[500,3000,500],analogue_gain_code=512),indent=2)+'\n')
print('Prepared independent RAW exposure probe; it does not claim a dark scene.')
