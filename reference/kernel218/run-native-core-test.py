from pathlib import Path
import gzip,hashlib,host,json

here=Path(__file__).resolve().parent
binary=(host.PRIVATE/'native-quad-test218').read_bytes()
assert binary[:4]==b'\x7fELF' and int.from_bytes(binary[18:20],'little')==183
payload=gzip.compress(binary,mtime=0)
path='/var/lib/samurai/k218-native-core'
code=r'''
from pathlib import Path
import os
root=Path('/var/lib/samurai');out=root/'k218-native-core'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not out.exists();out.mkdir(mode=0o700);(out/'probe.gz').touch(mode=0o600)
print('ready')
'''
assert host.ssh('python3 -',input=code.encode(),timeout=30).stdout.strip()==b'ready'
for offset in range(0,len(payload),65536):
    chunk=payload[offset:offset+65536]
    code="import sys,hashlib;from pathlib import Path;p=Path("+repr(path+'/probe.gz')+");b=sys.stdin.buffer.read();assert len(b)=="+str(len(chunk))+" and hashlib.sha256(b).hexdigest()=="+repr(hashlib.sha256(chunk).hexdigest())+";assert p.stat().st_size=="+str(offset)+";p.open('ab').write(b);print('ok')"
    assert host.ssh("python3 -c "+__import__('shlex').quote(code),input=chunk,timeout=30).stdout.strip()==b'ok'
code=r'''
from pathlib import Path
import gzip,hashlib,json,os,pwd,resource,subprocess,time
root=Path('/var/lib/samurai');out=root/'k218-native-core'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
data=gzip.decompress((out/'probe.gz').read_bytes());assert hashlib.sha256(data).hexdigest()==BINARY_SHA
probe=Path('/run/samurai-camera218-probes/native-quad-test');probe.parent.mkdir(mode=0o755,exist_ok=True);assert not probe.exists();probe.write_bytes(data);probe.chmod(0o755)
def demote():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    user=pwd.getpwuid(10000);os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
before=subprocess.check_output(['dmesg']);started=time.monotonic()
result=subprocess.run([str(probe),'--full'],capture_output=True,timeout=45,preexec_fn=demote)
(out/'stdout.json').write_bytes(result.stdout);(out/'stderr-private.log').write_bytes(result.stderr)
assert result.returncode==0
test=json.loads(result.stdout);assert test['passed'] and test['full_output_bytes']==4608*3456*3
after=subprocess.check_output(['dmesg'])
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k218-baseline/installed-before-private.txt').read_bytes()
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
report=dict(stage=218,test=test,native_arm_cpu=True,run_uid=10000,synthetic_input_only=True,
            scene_camera_not_started=True,three_full_native_size_frames=True,
            elapsed_seconds=time.monotonic()-started,max_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            installed_packages_unchanged=True,taint=0,fault_counts=faults)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('BINARY_SHA',repr(hashlib.sha256(binary).hexdigest()))
p=host.ssh('python3 -',input=code.encode(),timeout=65)
(host.PRIVATE/'native-core-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
(here/'native-core-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
