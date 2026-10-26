"""Offline host orchestration tests. No transport/collector/phone is invoked."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import base64
import copy
import datetime as dt
import importlib.util
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('host_launcher',HERE/'host-launcher.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
NONCE='a'*48
NOW=dt.datetime(2026,10,23,0,0,10,tzinfo=dt.timezone.utc).timestamp()
gate={'owned_handle_checked':True,'host_trigger_utc':'2026-10-23T00:00:10+00:00',
      'host_ready':{'armed':True,'target_port':7,'remaining_seconds_at_trigger':120,
                    'decoder_sha256':h.DECODER,'collector_sha256':h.COLLECTOR,'host_worker_pid':123,
                    'capture_id':'usb500-r6-'+NONCE,'ready_at_utc':'2026-10-23T00:00:09+00:00'}}
cases=[]
def case(name):cases.append(name)
def reject(call):
    try:call()
    except (ValueError,FileExistsError,RuntimeError):return
    raise AssertionError('invalid proof accepted')

h.validate_gate(gate,NONCE,NOW);case('actual-valid-owned-fresh-host-gate')
for field,value in [('owned_handle_checked',False),('host_trigger_utc','2026-10-23T00:00:04+00:00')]:
    bad=copy.deepcopy(gate);bad[field]=value
    reject(lambda:h.validate_gate(bad,NONCE,NOW))
case('actual-unowned-or-old-trigger-refused')
for field,value in [('ready_at_utc','2026-10-23T00:00:06+00:00'),('remaining_seconds_at_trigger',109),
                    ('decoder_sha256','0'*64),('target_port',True)]:
    bad=copy.deepcopy(gate);bad['host_ready'][field]=value
    reject(lambda:h.validate_gate(bad,NONCE,NOW))
case('actual-stale-sweep-short-time-wrong-source-or-port-type-refused')
bad=copy.deepcopy(gate);bad['host_trigger_utc']='2026-10-23T00:00:10'
reject(lambda:h.validate_gate(bad,NONCE,NOW));case('timezone-missing-refused')

# Only compile remote programs, and execute their actual ready/config mapping
# assignment nodes (no remote filesystem/process code).
compile(h.REMOTE_LAUNCH,'remote-launch','exec');compile(h.REMOTE_FETCH,'remote-fetch','exec')
tree=ast.parse(h.REMOTE_LAUNCH)
nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(
    isinstance(t,ast.Name) and t.id in ('ready','config') or
    isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='ready' for t in n.targets)]
env={'data':{'gate':gate,'manifest_sha256':h.MANIFEST,'token':'token','nonce':NONCE,
             'files':{'worker.py':{'sha256':h.REVIEWED['worker.py']}}},'guard':'guard','boot':'same-boot','sha':h.sha,
     'serial':b'synthetic-only','compat':b'synthetic-only'}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-remote-mapping','exec'),env)
assert env['config']['host_ready']['armed_utc']==gate['host_ready']['ready_at_utc']
assert env['config']['host_ready']['ready_at_utc']==gate['host_ready']['ready_at_utc']
case('actual-remote-syntax-and-frozen-worker-armed-utc-bridge')

def receipt(nonce):
    return {'pid':42,'start_ticks':12345,'argv':['python3','-B',h.PREFIX+nonce+'/worker.py','--worker',h.PREFIX+nonce],
            'worker_sha256':h.REVIEWED['worker.py']}
def envelope(nonce=NONCE,state='absent'):
    raw={n:(HERE/'device-candidate'/n).read_bytes() for n in h.REVIEWED}
    raw.update({'launch-receipt-private.json':json.dumps(receipt(nonce)).encode(),
                'execution-started-private.json':json.dumps({'nonce':nonce,'pid':42}).encode(),
                'worker.pid':b'42','config-private.json':json.dumps({'host_trigger_nonce':nonce,'manifest_sha256':h.MANIFEST,
                    'worker_sha256':h.REVIEWED['worker.py'],'identity':{'boot_id':'same-boot'}}).encode(),
                'result.json':json.dumps({'transaction':h.TX,'host_trigger_nonce':nonce,'terminal':True,'mutating_state_unknown':False,
                                          'diagnostic_completed':True,'passed':False,'restore100_verified':True}).encode()})
    return {'process_state':state,'receipt':receipt(nonce),'files':{n:{'sha256':h.sha(b),'base64':base64.b64encode(b).decode()} for n,b in raw.items()}}

with tempfile.TemporaryDirectory(prefix='usb500-host-tests-') as temp:
    private=Path(temp);(private/'r6-update').mkdir()
    (private/'r6-update/handoff-private.json').write_text(json.dumps({'manifest_sha256':h.MANIFEST,'observation':{'state':{'boot_id':'same-boot'}}}))
    gatefile=private/'gate.json';gatefile.write_text(json.dumps(gate))
    calls=[]
    def unknown(command,**kw):
        req=json.loads(kw['input']);calls.append(req)
        assert req['dispatch_count']==1 and req['reviewed']==h.REVIEWED
        raise subprocess.TimeoutExpired('fake-strict-ssh',30)
    with patch.object(h.time,'time',return_value=NOW):
        try:h.run('launch',NONCE,gatefile,True,ssh=unknown,private=private)
        except subprocess.TimeoutExpired:pass
        else:raise AssertionError('unknown transport did not propagate')
        reject(lambda:h.run('launch',NONCE,gatefile,True,ssh=unknown,private=private))
    out=private/('usb500-r6-'+NONCE)
    assert len(calls)==1 and (out/'launch-request-private.json').exists() and list(out.glob('*unknown-private.json'))
    case('actual-unknown-launch-durable-marker-no-second-dispatch')

    data=envelope()
    def fetch(command,**kw):
        assert h.REMOTE_FETCH in command or 'process_state' in command
        return SimpleNamespace(returncode=0,stdout=json.dumps(data).encode(),stderr=b'')
    report=h.run('fetch',NONCE,ssh=fetch,private=private)
    assert report['terminal_verified'] and report['result']['restore100_verified']
    assert (Path(report['retained_directory'])/'worker.py').read_bytes()==(HERE/'device-candidate/worker.py').read_bytes()
    case('actual-fetch-binds-process-config-marker-result-and-staged-hashes')

    data=envelope(state='alive')
    assert not h.run('fetch',NONCE,ssh=fetch,private=private)['terminal_verified']
    data={'process_state':'unknown','receipt':{},'files':{}}
    assert not h.run('fetch',NONCE,ssh=fetch,private=private)['terminal_verified']
    case('alive-or-missing-receipt-never-claims-worker-exit')

    data=envelope();data['files']['worker.py']['sha256']='0'*64
    reject(lambda:h.run('fetch',NONCE,ssh=fetch,private=private))
    data=envelope();data['receipt']['argv'][1]='-different'
    reject(lambda:h.run('fetch',NONCE,ssh=fetch,private=private))
    case('digest-or-process-fingerprint-mismatch-retains-raw-and-refuses-attestation')

    data=envelope();bad=json.loads(base64.b64decode(data['files']['result.json']['base64']));bad['host_trigger_nonce']='b'*48
    raw=json.dumps(bad).encode();data['files']['result.json']={'sha256':h.sha(raw),'base64':base64.b64encode(raw).decode()}
    reject(lambda:h.run('fetch',NONCE,ssh=fetch,private=private))
    data=envelope();data['files']['../escape']={'sha256':h.sha(b'x'),'base64':'eA=='}
    reject(lambda:h.run('fetch',NONCE,ssh=fetch,private=private))
    assert not (private/'escape').exists() and len(list(out.glob('fetch-*-stdout-private.json')))>=6
    case('wrong-result-nonce-or-path-traversal-refused-with-original-envelope-kept')

# No 51/62 suite is rerun. Hash-only locks on their frozen bytes and receipts.
for name,digest in h.REVIEWED.items():assert h.sha((HERE/'device-candidate'/name).read_bytes())==digest
case('exact-reviewed-b9f-worker-and-51-case-receipt-locked')
ps=json.loads((HERE/'parent-gate-test-result.json').read_text(encoding='utf-8-sig'))
assert ps['passed'] and not ps['usb_reader_started'] and not ps['network_accessed'] and not ps['device_accessed']
assert ps['tested_parent_sha256']==h.sha((HERE/'host-parent.ps1').read_bytes())
assert ps['test_script_sha256']==h.sha((HERE/'test-host-parent.ps1').read_bytes())
tested={n:h.sha((HERE/n).read_bytes()) for n in ['host-launcher.py','host-parent.ps1','test-orchestration.py','test-host-parent.ps1','watch-one-hub.ps1','UsbHubReadOnly.cs']}
result={'passed':True,'python_cases':len(cases),'python_case_names':cases,'powershell_cases':ps['cases'],
        'tested_files':tested,'frozen_device_files':h.REVIEWED,
        'remote_launch_sha256':h.sha(h.REMOTE_LAUNCH.encode()),'remote_fetch_sha256':h.sha(h.REMOTE_FETCH.encode()),
        'network_accessed':False,'device_accessed':False,'usb_reader_started':False,'prior_51_or_62_suite_rerun':False}
(HERE/'orchestration-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'python_cases':len(cases),'powershell_cases':ps['cases'],'tested_files':tested},indent=2))
