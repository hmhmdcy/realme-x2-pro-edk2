import host
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');state=json.loads((root/'k222-sof-trial/state-private.json').read_text());assert state['phase']=='original-restored'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k222-baseline/boot-id-private.txt').read_bytes()
source=root/'k222-sof-modules/gap-runner.py';target=source.with_name('gap-runner-r2.py');assert not target.exists()
text=source.read_text();old="tag='request-gap-sof-candidate'";assert text.count(old)==1;target.write_text(text.replace(old,"tag='request-gap-sof-candidate-r2'"))
print('K222_NATIVE_R2_RUNNER_STAGED_OLD_CAPTURE_RECORDS_PRESERVED')
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25);print(p.stdout.decode())
