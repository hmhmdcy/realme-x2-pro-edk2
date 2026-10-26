"""Retain the existing numerical-only probe; use new guard and ambient light."""
from pathlib import Path
import gzip,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'pmic-cycles-validation.json').read_text())['front_sensor_rebound_and_suspended']
binary=host.PRIVATE.parent/'kernel219/native-mode-probe219';data=binary.read_bytes()
proof=json.loads((R.parent/'kernel219/native-probe-build-validation.json').read_text());assert hashlib.sha256(data).hexdigest()==proof['probe_sha256']
code="from pathlib import Path;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes();out=root/'k233-front-probe-stage';assert not out.exists();out.mkdir(mode=0o700);(out/'probe.gz').touch(mode=0o600)"
host.ssh('python3 -c '+shlex.quote(code),timeout=15)
payload=gzip.compress(data,mtime=0)
for offset in range(0,len(payload),48*1024):
 block=payload[offset:offset+48*1024]
 code="from pathlib import Path;import sys,hashlib;p=Path('/var/lib/samurai/k233-front-probe-stage/probe.gz');data=sys.stdin.buffer.read();assert p.stat().st_size==%d;assert len(data)==%d and hashlib.sha256(data).hexdigest()==%r;p.open('ab').write(data)"%(offset,len(block),hashlib.sha256(block).hexdigest())
 host.ssh('python3 -c '+shlex.quote(code),input=block,timeout=20)
code="from pathlib import Path;import gzip,hashlib;p=Path('/run/samurai-camera233-probes');assert not p.exists();p.mkdir(mode=0o755);data=gzip.decompress(Path('/var/lib/samurai/k233-front-probe-stage/probe.gz').read_bytes());assert hashlib.sha256(data).hexdigest()==%r;f=p/'native-mode-probe';f.write_bytes(data);f.chmod(0o755)"%proof['probe_sha256']
host.ssh('python3 -c '+shlex.quote(code),timeout=20)
text=(R.parent/'kernel229/native-daylight-baseline.py').read_text()
text=text.replace("guard=root/'k228-runtime/boot-id-private.txt'","guard=root/'k233-runtime/boot-id-private.txt'")
text=text.replace("read_text().strip()=='4096'","read_text().strip()=='0'").replace("=={'fastrpc':'O'}","=={}")
text=text.replace('k229-capture-daylight-baseline-','k233-front-regression-').replace('stage=229','stage=233')
text=text.replace('/run/samurai-camera229-probes/','/run/samurai-camera233-probes/')
text=text.replace("lighting_condition='user reports daylight'","lighting_condition='ambient light, no colour reference target'")
compile(text,'front-regression233','exec');(R/'native-front-regression.py').write_text(text)
report=dict(stage=233,original_ram_only_probe_sha256=proof['probe_sha256'],no_new_sdk_build=True,
 native_runner_new_guard=True,scene_pixels_not_saved=True,known_colour_test_still_deferred=True)
(R/'front-probe-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
