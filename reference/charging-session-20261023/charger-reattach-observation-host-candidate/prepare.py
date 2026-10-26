"""Explicit local preparation; no network or runtime request."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=REF/'charging-oem-audit-20261023/protection-capture-host-candidate'
WORKER=HERE.parent/'charger-reattach-observation-update-candidate'
PACK=HERE.parent/'charger-reattach-observation-payload-candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    assert sys.argv[1:]==['--prepare']
    assert sha((BASE/'delivery.json').read_bytes())=='720ea40e8c81f514f5211dd5adb00b54052b7c355690bc91d5f2ab7ace6a42e6'
    original=json.loads((BASE/'delivery.json').read_bytes())
    source=(BASE/'remote.py').read_text();assert sha((BASE/'remote.py').read_bytes())==original['files']['remote.py']['sha256']
    changes=[('protection-capture-[a-z0-9-]{8,48}','charger-reattach-update-[a-z0-9-]{8,48}'),
             ('samurai-protection-capture-request-v1','samurai-charger-reattach-update-v1'),
             ("out = root / 'device-stage'","out = root / 'device-update'")]
    for before,after in changes:assert source.count(before)==1;source=source.replace(before,after)
    for name,data in [('remote.py',source.encode()),('supervisor.py',(BASE/'supervisor.py').read_bytes())]:
        path=HERE/name
        if path.exists():assert path.read_bytes()==data
        else:path.write_bytes(data)
    inherited=json.loads((BASE/'source-pins.json').read_bytes())
    entries={name:inherited[name] for name in ['adoption_review','adoption_review_pins','original_delivery','original_host','original_remote','original_supervisor','key_transport']}
    def add(name,path):
        path=path.resolve();data=path.read_bytes();entries[name]={'path':path.as_posix(),'sha256':sha(data),'bytes':len(data)}
    for name,path in [('worker',WORKER/'stage-worker.py'),('worker_delivery',WORKER/'delivery.json'),
                      ('payload_delivery',PACK/'delivery.json'),('payload_result',PACK/'payload-result.json'),
                      ('capture_delivery',BASE/'delivery.json'),('base_remote',BASE/'remote.py'),
                      ('preflight_profile',REF/'charging-oem-audit-20261023/irq-postboot-compressed-profile/profile.py')]:add(name,path)
    receipt=json.loads((PACK/'payload-result.json').read_bytes())
    add('payload',Path(receipt['forward']['path']))
    for name in ['host','remote','supervisor']:add(name,HERE/(name+'.py'))
    path=HERE/'source-pins.json';assert not path.exists();path.write_text(json.dumps(entries,indent=2)+'\n',encoding='utf-8')
    (HERE/'remote-profile.json').write_text(json.dumps({'original_remote_sha256':sha((BASE/'remote.py').read_bytes()),'changes':changes,'original_supervisor_byte_exact':True},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'prepared':True,'runtime_request_created':False,'device_accessed':False}))
if __name__=='__main__':main()
