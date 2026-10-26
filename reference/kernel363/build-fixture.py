from pathlib import Path
import hashlib,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent
prior=HERE/'camera-runtime-validation.json'
assert not json.loads(prior.read_text())['passed']
(HERE/'camera-runtime-r1-validation.json').write_bytes(prior.read_bytes())
s=(HERE.parent/'kernel313/pipeline-fixture.c').read_text();old=s
s=s.replace('7.3.0-rc6-rmx1931-samurai-k298+','7.3.0-rc6-rmx1931-samurai-k363+').replace('"#298 "','"#363 "')
assert s!=old and s.count('"#363 "')==1
(HERE/'pipeline-fixture.c').write_text(s)
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-std=gnu17','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
 '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'pipeline-fixture.c'),'-o',str(host.PRIVATE/'pipeline-fixture')],capture_output=True)
(host.PRIVATE/'fixture-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
q=host.ssh('/var/lib/samurai/k362-install-r1/pipeline-fixture /dev/media0 /bin/true',timeout=20,check=False)
assert q.returncode==3 and not q.stdout and not q.stderr
report=dict(stage=363,fixture_version_guard_updated_only=True,old_actual_exit=3,old_guard_stops_before_media_access=True,new_static_aarch64_build_passed=True,sha256=hashlib.sha256((host.PRIVATE/'pipeline-fixture').read_bytes()).hexdigest(),passed=True)
(HERE/'fixture-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
