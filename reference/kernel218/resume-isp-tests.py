from pathlib import Path
import host,json

here=Path(__file__).resolve().parent
original=(here/'stage-and-run-isp-tests.py').read_text().rsplit("code=r'''",1)[1].split("'''",1)[0]
tail=original[original.index("before=subprocess.check_output(['dmesg'])"):]
old="assert match and Path(match[1]).resolve()==(prefix/'usr/lib'/(lib+'.so.0.7.2')).resolve()"
assert tail.count(old)==1
tail=tail.replace(old,"if match:assert Path(match[1]).resolve()==(prefix/'usr/lib'/(lib+'.so.0.7.2')).resolve()\n        else:assert executable=='native-quad', 'Missing required camera library'")
head=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,resource,subprocess,time
root=Path('/var/lib/samurai');out=root/'k218-cpu-isp-tests-r2';prefix=Path('/run/samurai-camera218-cpu')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
old=root/'k218-cpu-isp-tests'
assert (old/'native-quad-ldd-private.log').exists() and not (old/'native-quad-stdout-private.log').exists()
ldd=(old/'native-quad-ldd-private.log').read_text()
assert 'libcamera.so' not in ldd and 'libcamera-base.so' not in ldd
assert not out.exists();out.mkdir(mode=0o700)
manifest=json.loads((prefix/'manifest.json').read_text())
for name,record in manifest.items():
    p=prefix/name
    if 'target' in record:assert p.is_symlink() and os.readlink(p)==record['target']
    else:assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256']
'''
code=head+tail
compile(code,'native-cpu-isp218-r2','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=210)
(host.PRIVATE/'cpu-isp-tests-r2-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
report['initial_preflight_failed_on_header_only_test_without_camera_dynamic_dependency']=True
report['initial_preflight_before_any_test_execution']=True
(here/'cpu-isp-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
