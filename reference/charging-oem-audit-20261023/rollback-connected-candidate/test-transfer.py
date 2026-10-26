"""Three new actual transfer branches; authentication and process IO are fake."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,hashlib,importlib.util,json,os,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    h=load(HERE/'host.py','actual_transfer_host');pins,_=h.source_check();cases=[]
    req=dict(transaction_id='usb-irq-protection-rollback-transfer001',identity=dict(boot_id='00000000-0000-4000-8000-000000000502'))
    raw=(json.dumps(req)+'\n').encode();binding=dict(endpoint=dict(peer=h.PEER,host_key_alias=h.ALIAS,observed_new_boot=req['identity']['boot_id']))
    with tempfile.TemporaryDirectory(prefix='rollback-transfer-synthetic-') as tmp:
        root=Path(tmp);(root/'restore-worker.py').write_bytes(h.local(pins['worker']['path']).read_bytes())
        events=[]
        def bound(tx,launching=False):
            assert tx==req['transaction_id'];events.append(('bound',launching));return root,binding,req,raw,pins
        def save(path,value):path.write_text(json.dumps(value)+'\n')
        def start(directory,action,code,argv):
            events.append(('start',action));assert directory==root
            tree=ast.parse(code.decode());assert tree.body[0].targets[0].id=='ROLLBACK_TRANSPORT'
            envelope=ast.literal_eval(tree.body[0].value)
            assert envelope['request']==req and envelope['request_sha256']==sha(raw)
            assert code.endswith((HERE/'remote.py').read_bytes())
            assert '-6' in argv and 'StrictHostKeyChecking=yes' in argv and 'root@'+h.PEER in argv and 'HostKeyAlias='+h.ALIAS in argv
            assert (root/'launch-intent-private.json').exists()
            if action=='launch':
                assert base64.b64decode(envelope['worker_base64'])==(root/'restore-worker.py').read_bytes()
                assert base64.b64decode(envelope['supervisor_base64'])==(HERE/'supervisor.py').read_bytes()
                return dict(pending=True,job='original-owned-job',unknown_means_fetch_only=True)
            call=root/'fetch-job';call.mkdir();return dict(pending=False,job=str(call),owner_returncode=0)
        with patch.object(h,'bound',bound),patch.object(h,'os',SimpleNamespace(name='posix')),patch.object(h,'local',Path),patch.object(h,'save',save),patch.object(h,'start_job',start):
            try:h.transfer('launch',req['transaction_id'],False)
            except ValueError:pass
            else:raise AssertionError('uncoordinated window accepted')
            assert not (root/'launch-intent-private.json').exists() and not [x for x in events if x[0]=='start']
            cases.append('actual_launch_no_window_no_intent_or_process')
            value=h.transfer('launch',req['transaction_id'],True)
            assert value['pending'] is True and events[-1]==('start','launch')
            try:h.transfer('launch',req['transaction_id'],True)
            except ValueError:pass
            else:raise AssertionError('unknown launch replayed')
            assert len([x for x in events if x==('start','launch')])==1
            cases.append('actual_launch_original_key_exact_wire_once_pending_no_replay')
            response=dict(transaction_id=req['transaction_id'],request_sha256=sha(raw))
            def no_clean_original(*args):raise ValueError('original launch terminal0 unproved')
            with patch.object(h,'terminal_job',lambda p:(dict(returncode=0),response)),patch.object(h,'accept_fetch',lambda *a:dict(rollback_staged_original=True,runtime_validation_accepted=False)),patch.object(h,'review_launch_transport',no_clean_original):
                result=h.transfer('fetch',req['transaction_id'])
            assert result['rollback_staged_original'] is False and result['original_launch_transport_terminal'] is False
            assert result['runtime_validation_accepted'] is False and (root/'fetch-job/received-result-private.json').exists()
            cases.append('actual_fetch_retains_response_but_unproved_original_launch_not_promoted')
    result=dict(passed=True,case_count=len(cases),cases=cases,tested_files={name:sha((HERE/name).read_bytes()) for name in ('host.py','test-transfer.py')},
        actual_functions=['transfer'],fake_boundaries=['bound authenticated inputs','Popen owner jobs and output terminal','accept_fetch/review_launch_transport outcome; actual reviewers covered by wire receipt'],
        runtime_material_or_lease_generated=False,device_or_transport_accessed=False,old_suites_rerun=False)
    (HERE/'test-transfer-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result))


if __name__=='__main__':main()
