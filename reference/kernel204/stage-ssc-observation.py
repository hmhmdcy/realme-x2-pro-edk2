from pathlib import Path
import ast,hashlib,json
import host

here=Path(__file__).resolve().parent;source=here.parents[1]/'linux-port/ssc/samurai-ssc.py';ast.parse(source.read_text());digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.upload(source,'/var/lib/samurai/k204-reboot-tools/samurai-ssc-observation.py')
native=r'''
from pathlib import Path
import hashlib,json,os,shutil
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
current=Path('/usr/sbin/samurai-ssc');old=(root/'k204-ssc-failure/service-source-private.py').read_bytes();assert current.read_bytes()==old
state=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert state['stopped'] and not state['started']
out=root/'k204-ssc-observation-deploy';assert not out.exists();out.mkdir(mode=0o700);(out/'original.py').write_bytes(old)
candidate=root/'k204-reboot-tools/samurai-ssc-observation.py';new=candidate.read_bytes();assert hashlib.sha256(new).hexdigest()==EXPECTED
temporary=current.with_name('samurai-ssc.k204-new');temporary.write_bytes(new);temporary.chmod(0o755);os.replace(temporary,current)
report=dict(stage=204,only_readiness_failure_recording_added=True,source_sha256=EXPECTED,original_source_preserved=True,failed_instance_not_restarted=True,new_boot_required_for_next_attempt=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=native.replace('EXPECTED',repr(digest)).encode());(host.PRIVATE/'ssc-observation-deploy-private.log').write_bytes(p.stdout+p.stderr);(here/'ssc-observation-validation.json').write_bytes(p.stdout);print(p.stdout.decode())
