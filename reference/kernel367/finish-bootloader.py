from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert (P/'reboot-request-private.json').exists() and not (P/'fastboot-reboot-request-private.json').exists()
fb='/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
q=subprocess.run([fb,'devices'],capture_output=True,timeout=15);(P/'fastboot-devices-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
found=re.findall(r'(?m)^(\S+)\s+fastboot\s*$',q.stdout.decode());assert len(found)==1
expected=json.loads((P.parent/'kernel109/fastboot-identity.json').read_text())['serial'];assert found[0]==expected
q=subprocess.run([fb,'-s',expected,'getvar','product'],capture_output=True,timeout=15);q.check_returncode();assert re.search(r'product:\s*msmnile\b',(q.stdout+q.stderr).decode())
(P/'fastboot-reboot-request-private.json').write_text(json.dumps(dict(request_count=1,partitions_written=[])))
q=subprocess.run([fb,'-s',expected,'reboot'],capture_output=True,timeout=20);(P/'fastboot-reboot-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
d=dict(stage=367,fresh_fastboot_identity_verified=True,reboot_requested_once=True,partitions_written=[],kernel_firmware_and_logdump_unchanged=True)
(HERE/'restart-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
