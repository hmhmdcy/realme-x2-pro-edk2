"""R2 deadline/bounds/pin-mixing only; actual functions, fake OS/SSH boundary."""
from pathlib import Path
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import ast,json,tempfile
import common,protocol,gates,observer,controller
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-usbin-init-host-candidate'
cases=[]
def check(name,value):assert value,name;cases.append(name)
def rejects(fn,text=''):
    try:fn()
    except (ValueError,FileExistsError) as e:return text in str(e)
    return False
f={k:protocol.parse(v) for k,v in json.loads((HERE/'actual-state-fixtures.json').read_text()).items()}
waiting=f['waiting_after_61s'];now=waiting['now_boottime_ms']
check('actual state_show still waiting after61s in exact300000 window',protocol.waiting(waiting,now,45000) and waiting['deadline_boottime_ms']-waiting['started_boottime_ms']==300000)
oldf={k:protocol.parse(v) for k,v in (l.split('\t',1) for l in (OLD/'actual-fixtures/stdout.jsonl').read_text().splitlines())}
check('actual R1 60000 waiting cannot authorize R2 prompt',not protocol.waiting(oldf['waiting'],oldf['waiting']['now_boottime_ms'],45000))
for delta in [-1,1]:
    s=deepcopy(waiting);s['deadline_boottime_ms']+=delta;s['remaining_ms']+=delta
    check('nonexact window rejected '+str(delta),not protocol.waiting(s,now,45000))
s=deepcopy(waiting);s['now_boottime_ms']=s['deadline_boottime_ms']-45000;s['remaining_ms']=45000
check('exact45s readiness preserved',protocol.waiting(s,s['now_boottime_ms'],45000))
s['now_boottime_ms']+=1;s['remaining_ms']-=1
check('below45s rejected',not protocol.waiting(s,s['now_boottime_ms'],45000))
check('actual300s zero-write expiry remains closable',protocol.close_zero_write(f['timeout_at_300s']) and protocol.close_zero_write(f['blocked_prewrite_at_deadline']))
class Admitted(Exception):pass
for seconds,admit in [(480,True),(600,True),(601,False),(89,False)]:
    with patch.object(observer.icon,'RealIO',side_effect=Admitted),patch.object(observer.os,'umask',return_value=0):
        try:observer.run({'execute':True,'window_confirmed':True,'max_seconds':seconds})
        except Admitted:actual=True
        except ValueError:actual=False
    check('actual observer bound '+str(seconds),actual==admit)
real_inputs=controller.local_inputs(require_tests=False)
check('actual frozen R2 KO protocol core build fixture pins pass',common.sha(real_inputs[0]['samurai-usbin-init.ko'])=='2edcafa86335a2c01be52058c3432c82241460b692e1c638e08f7ce071098f78')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);calls=[]
    def ssh(command,**kw):
        incoming=json.loads(ast.literal_eval(kw['input'].decode().split('io.BytesIO(',1)[1].split('))\n',1)[0]));calls.append(incoming)
        return SimpleNamespace(returncode=0,stdout=json.dumps({'instance':f['observed']['instance']}).encode(),stderr=b'')
    with patch.object(controller,'local_inputs',return_value=(real_inputs[0],'fake-boot','fake-guard',{})):
        opts=dict(execute=True,window_confirmed=True,ssh=ssh,private=root,require_tests=False)
        controller.run('launch','usbin-init-r8-002',**opts)
        check('actual launch passes480 once to new002',len(calls)==1 and calls[0]['max_seconds']==480 and calls[0]['transaction']=='usbin-init-r8-002')
        check('002 dispatch remains one-shot',rejects(lambda:controller.run('launch','usbin-init-r8-002',**opts)) and len(calls)==1)
        (root/'usbin-init-r8-001').mkdir()
        check('existing001 never reused',rejects(lambda:controller.run('launch','usbin-init-r8-001',**opts)) and len(calls)==1)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);pins=json.loads((HERE/'input-pins.json').read_text());bad=root/'old-protocol.json';bad.write_bytes((OLD/'helper-protocol.json').read_bytes())
    pins['helper_protocol']={'path':str(bad),'sha256':common.sha(bad.read_bytes())};(root/'input-pins.json').write_text(json.dumps(pins))
    with patch.object(controller,'HERE',root):check('actual local_inputs rejects pinned old60 protocol with R2 delivery',rejects(lambda:controller.local_inputs(False),'exactly 300000'))
    (root/'input-pins.json').write_bytes((HERE/'input-pins.json').read_bytes())
    for name in controller.RUNTIME:(root/name).write_bytes((OLD/name if name=='samurai-usbin-init.ko' else HERE/name).read_bytes())
    with patch.object(controller,'HERE',root):check('actual local_inputs rejects oldKO/newR2 evidence mixture',rejects(lambda:controller.local_inputs(False),'helper module differs'))
for name in ['common.py','gates.py','device.py','icon-observation.py','icon-audit.py']:
    assert (HERE/name).read_bytes()==(OLD/name).read_bytes(),name
check('identity readiness safety UI unknown qualify close runtime byte-preserved',True)
compile(controller.BOOTSTRAP,'remote-bootstrap','exec')
files={name:common.sha((HERE/name).read_bytes()) for name in controller.RUNTIME+['controller.py','input-pins.json','helper-protocol.json','actual-state-fixtures.json','test-r2.py','prepare-r2.py','reused-r1-test-result.json','reused-r1-delivery.json']}
receipt={'passed':True,'case_count':len(cases),'cases':cases,'files':files,'worker_sha256':files['device.py'],
 'scope':'R2 deadlines observer bounds actual launch480 and artifact-mixing boundaries only','R1_35_cases_reused_not_rerun':True,
 'OEM_fixture_sha256':files['actual-state-fixtures.json'],'no_phone_network_SDK_Git':True,'launch_executed':False}
common.save(HERE/'test-result.json',receipt)
print(json.dumps({'passed':True,'new_case_count':len(cases),'old35_rerun':False,'actual_launch_boundary':'fake SSH only'}))
