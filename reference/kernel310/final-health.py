"""Inspect only this stage's process handles and the current camera module."""
from pathlib import Path
import json,re,shlex
import host
HERE=Path(__file__).resolve().parent
pids=set()
for kind in ['delay','joint']:
    data=json.loads((host.PRIVATE/(kind+'-r1-results.json')).read_text())
    pids.add(data['state']['pid'])
    for text in data['logs'].values():
        pids.update(map(int,re.findall(r'(?:APPLICATION_PROCESS pid=|IPA init pid=|STEPPER_READY pid=)(\d+)',text)))
code=r'''
from pathlib import Path
import hashlib,json
live=[]
for pid in PIDS:
    p=Path('/proc',str(pid))
    try:
        if (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
            live.append({'pid':pid,'command':(p/'comm').read_text().strip()})
    except FileNotFoundError:pass
result={'live_stage_processes':live,'loaded_camss_note_sha256':hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
        'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()}
print(json.dumps(result))
'''.replace('PIDS',repr(sorted(pids)))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
result=json.loads(q.stdout)
joint=json.loads((HERE/'joint-r1-validation.json').read_text())
result.update(stage=310,health=joint['capture']['health'],fault_delta=joint['capture']['fault_delta'],
              consumers_unchanged=joint['capture']['consumers_unchanged'],whole_system_healthy=False)
result['passed']=not result['live_stage_processes'] and result['same_boot'] and joint['capture']['passed'] and result['loaded_camss_note_sha256']=='19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113'
(HERE/'final-health-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
