"""Only new wire/owner boundaries; IO, authentication and process interfaces fake.

All request identities below are synthetic temporary fixtures, never runtime
material. Actual frozen source/profile/probe authentication is reused, not rerun.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,io,json,os,subprocess,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encode=lambda v:(json.dumps(v,indent=2)+'\n').encode()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    h=load(HERE/'host.py','actual_connected_host');h.source_check()
    w=load(HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py','frozen_restore_identities')
    cases=[]
    def passed(name):cases.append(name)
    def reject(name,fn):
        try:fn()
        except (OSError,ValueError,KeyError,TypeError,AssertionError):passed(name)
        else:raise AssertionError('accepted: '+name)
    worker_raw=(HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py').read_bytes()
    sup_raw=(HERE/'supervisor.py').read_bytes()
    payload=Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01/rollback-r8-payload.tar.gz').read_bytes()
    def request(profile=w.PROFILES[0],suffix='synthetic001'):
        ident=dict(boot_id='00000000-0000-4000-8000-000000000502',version=w.VERSION,
            serial_sha256=sha(b'serial\n'),compatible_sha256=sha(b'realme,samurai\0'),rootfs_sha256=sha(b'rootfs\n'))
        return dict(schema='samurai-usb-irq-protection-rollback-request-v1',transaction_id='usb-irq-protection-rollback-'+suffix,
            profile=profile,identity=ident,source_identity=copy.deepcopy(ident),source_stage={},activation=None,
            payload_sha256=sha(payload),payload_base64=base64.b64encode(payload).decode(),worker_sha256=sha(worker_raw),lease_token='e'*48)
    def simple_save(path,value):path.write_bytes(encode(value))
    with tempfile.TemporaryDirectory(prefix='rollback-connected-synthetic-') as temporary:
        temp=Path(temporary)
        # Real binder is reached and rejects absent originals before parent mkdir.
        with patch.object(h,'PRIVATE',temp/'must-not-exist'):
            reject('actual_missing_evidence_before_runtime_mkdir',lambda:h.bind('usb-irq-protection-rollback-synthetic001',w.PROFILES[0],temp/'missing-stage',temp/'missing-fetch',temp/'missing-probe'))
            assert not h.PRIVATE.exists()

        # Execute the actual remote wrapper with Linux device FS and process
        # boundaries mapped into a temporary tree; no real /root or /run writes.
        def remote_fixture(req):
            r=load(HERE/'remote.py','actual_remote_'+req['transaction_id'].replace('-','_'))
            fs=temp/('remote-'+req['transaction_id']);fs.mkdir()
            def path(*parts):
                p=Path(*parts)
                text=str(p).replace('\\','/')
                return fs/text.lstrip('/').replace(':','_') if p.is_absolute() or text.startswith('/') else p
            r.Path=path;r.save=simple_save
            r.os=SimpleNamespace(umask=lambda x:None,geteuid=lambda:0,uname=lambda:SimpleNamespace(version=w.VERSION),fsync=os.fsync)
            r.time=SimpleNamespace(CLOCK_BOOTTIME=7,clock_gettime=lambda clock:1000.)
            for name,raw in [('/proc/sys/kernel/random/boot_id',(req['identity']['boot_id']+'\n').encode()),('/sys/devices/soc0/serial_number',b'serial\n'),
                ('/sys/firmware/devicetree/base/compatible',b'realme,samurai\0'),('/etc/samurai-rootfs-release',b'rootfs\n')]:
                p=path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            path('/root/charging-management-20261023').mkdir(parents=True);path('/run').mkdir()
            popens=[]
            def popen(argv,**kw):popens.append((argv,kw));return SimpleNamespace(pid=810)
            r.subprocess=SimpleNamespace(Popen=popen,DEVNULL=subprocess.DEVNULL,STDOUT=subprocess.STDOUT)
            r.process=lambda receipt,argv:dict(state='alive' if receipt else 'unknown')
            raw=encode(req)
            data=dict(action='launch',request=req,request_sha256=sha(raw),request_base64=base64.b64encode(raw).decode(),worker_base64=base64.b64encode(worker_raw).decode(),
                supervisor_base64=base64.b64encode(sup_raw).decode(),supervisor_sha256=sha(sup_raw),window_confirmed=True)
            return r,path,popens,data
        for index,profile in enumerate(w.PROFILES):
            req=request(profile,'synthetic00'+str(index));r,path,popens,data=remote_fixture(req)
            response=r.execute(data);root=path('/root/charging-management-20261023')/req['transaction_id']
            assert response['launched'] and len(popens)==1 and popens[0][0][-1]=='--execute-supervisor'
            assert (root/'restore-worker.py').read_bytes()==worker_raw and (root/'request-private.json').read_bytes()==encode(req)
            lease=json.loads(path('/run/'+req['transaction_id']+'-window-private.json').read_bytes())
            assert lease['expires_boottime_s']-lease['issued_boottime_s']==120 and lease['boot_id']==req['identity']['boot_id']
            assert all(lease[k] is True for k in ('exclusive','camera_released','bluetooth_released'))
            reject('remote_once_'+str(index),lambda:r.execute(data));assert len(popens)==1
            passed('remote_profile_'+str(index)+'_regular_request_and_exact120_lease')
            if index==0:
                (root/'launch-receipt-private.json').write_text('{')
                path('/proc/sys/kernel/random/boot_id').write_text('00000000-0000-4000-8000-000000000999\n')
                r.process=lambda *a:(_ for _ in ()).throw(AssertionError('must not inspect current same PID'))
                data['action']='fetch';value=r.execute(data)
                assert value['process']['state']==value['supervisor_process']['state']=='source_boot_ended'
                assert value['worker_terminal_verified'] is False and value['files']['launch-receipt-private.json']['bytes']==1
                passed('crossboot_fetch_raw_malformed_receipt_without_current_pid_or_launch')
        req=request(suffix='badidentity');r,path,popens,data=remote_fixture(req)
        path('/sys/devices/soc0/serial_number').write_text('different\n')
        reject('remote_current_identity_mismatch_zero_claim',lambda:r.execute(data));assert not popens and not (path('/root/charging-management-20261023')/req['transaction_id']).exists()

        # Actual detached device supervisor: request is regular FD; receipt failure
        # still joins this exact worker Popen and retains real return code.
        for fail in (False,True):
            s=load(HERE/'supervisor.py','actual_supervisor_'+str(fail));req=request(suffix='supervisor'+str(fail).lower())
            root=temp/req['transaction_id'];root.mkdir();raw=encode(req)
            for name,content in [('request-private.json',raw),('restore-worker.py',worker_raw),('rollback-supervisor.py',sup_raw)]: (root/name).write_bytes(content)
            simple_save(root/'launch-claim-private.json',dict(transaction_id=req['transaction_id'],request_sha256=sha(raw),supervisor_sha256=sha(sup_raw)))
            events=[]
            def popen(argv,**kw):
                assert kw['stdin'].read()==raw and kw['stdin'].seekable() and kw['stdin'].name==str(root/'request-private.json')
                assert argv[-1]=='--execute-rollback';events.append('popen')
                class Child:
                    pid=812
                    def wait(self):events.append('wait');return 9 if fail else 0
                return Child()
            s.subprocess=SimpleNamespace(Popen=popen,STDOUT=subprocess.STDOUT);s.ticks=lambda pid:pid+123
            def saving(path,value):
                if fail and path.name=='worker-launch-receipt-private.json':raise OSError('synthetic receipt failure')
                simple_save(path,value)
            s.save=saving
            if fail:reject('supervisor_receipt_failure_still_same_wait',lambda:s.supervise(root))
            else:s.supervise(root);passed('supervisor_regular_request_actual_worker_wait')
            assert events==['popen','wait'] and json.loads((root/'worker-terminal-private.json').read_bytes())['returncode']==(9 if fail else 0)
            assert (root/'supervisor-terminal-private.json').exists() is (not fail)

        # Actual local SSH owner: no payload sent after failed launch receipt;
        # partial communicate also closes this owned stdin and waits same Popen.
        for mode in ('ok','receipt','partial','log_close'):
            root=temp/('owner-'+mode);root.mkdir();code=b'# synthetic not executed\n';(root/'program.py').write_bytes(code)
            simple_save(root/'job.json',dict(program=str(root/'program.py'),stdin_sha256=sha(code),host_sha256=sha((HERE/'host.py').read_bytes()),argv=['synthetic-ssh']))
            events=[]
            class Child:
                pid=814;returncode=None
                def __init__(self):self.stdin=io.BytesIO()
                def communicate(self,input):
                    assert input==code;events.append('communicate')
                    if mode=='partial':raise BrokenPipeError('synthetic partial input')
                def wait(self):
                    assert self.stdin.closed;events.append('wait');self.returncode=0;return 0
            child=Child();real_save=h.save
            def saving(path,value):
                if mode=='receipt' and path.name=='transport-child-private.json':raise OSError('synthetic receipt failure before send')
                real_save(path,value)
            original_open=Path.open
            def opening(path,*args,**kwargs):
                stream=original_open(path,*args,**kwargs)
                if mode!='log_close' or path.name!='stdout-private.json' or args!=('xb',):return stream
                class CloseFailure:
                    def __getattr__(self,name):return getattr(stream,name)
                    def close(self):stream.close();raise OSError('synthetic owned log close failure')
                return CloseFailure()
            with patch.object(h,'PRIVATE',temp),patch.object(h,'process_identity',lambda pid:dict(pid=pid,startticks=123,argv=['synthetic-ssh'])),patch.object(h,'save',saving),patch.object(h,'subprocess',SimpleNamespace(Popen=lambda *a,**kw:child,PIPE=subprocess.PIPE)),patch.object(Path,'open',opening):
                if mode=='ok':assert h.ssh_owner(root/'job.json')==0;passed('local_owner_real_same_popen_terminal')
                else:reject('local_owner_'+mode+'_eof_same_wait',lambda:h.ssh_owner(root/'job.json'))
            assert events==(['wait'] if mode=='receipt' else ['communicate','wait'])
            terminal=json.loads((root/'transport-terminal-private.json').read_bytes())
            assert terminal['terminal'] is True and terminal['stdin_sha256']==sha(code) and terminal['returncode']==0
            assert bool(terminal['primary_error'])==(mode in ('receipt','partial'))
            if mode=='log_close':assert terminal['cleanup_errors'][0]['phase']=='stdout_close'

        # Bounded parent wait does not kill/communicate/relaunch or invent a
        # terminal. The detached original owner alone continues its child wait.
        root=temp/'pending';root.mkdir();events=[]
        class Pending:
            pid=816
            def wait(self,timeout):events.append(timeout);raise subprocess.TimeoutExpired('owned',timeout)
        with patch.object(h,'process_identity',lambda pid:dict(pid=pid,startticks=123,argv=['owned'])),patch.object(h,'subprocess',SimpleNamespace(Popen=lambda *a,**kw:Pending(),DEVNULL=subprocess.DEVNULL,STDOUT=subprocess.STDOUT,TimeoutExpired=subprocess.TimeoutExpired)):
            result=h.start_job(root,'launch',b'not executed', ['synthetic-ssh'])
        assert events==[35] and result['pending'] is True and not (Path(result['job'])/'owner-parent-terminal-private.json').exists()
        passed('parent35_timeout_pending_no_kill_no_terminal_no_relaunch')

        # Terminal/input and both parent/self owner identities are actual new
        # reviewer code; no PID absence can replace the original child wait.
        root=temp/'term';root.mkdir();code=b'not executed';(root/'executed-remote.py').write_bytes(code)
        argv=['synthetic-ssh'];owner=dict(pid=815,startticks=501,argv=['owned'])
        child=dict(pid=814,startticks=500,argv=argv,requested_argv=argv,stdin_sha256=sha(code))
        simple_save(root/'job-private.json',dict(stdin_sha256=sha(code),owner_argv=owner['argv'],argv=argv,host_sha256=sha((HERE/'host.py').read_bytes())))
        stdout=encode(dict(synthetic=True));(root/'stdout-private.json').write_bytes(stdout);(root/'stderr-private.txt').write_bytes(b'')
        term=dict(child,terminal=True,returncode=0,stdout_sha256=sha(stdout),stderr_sha256=sha(b''),primary_error=None,cleanup_errors=[])
        for name,value in [('owner-launch-private.json',owner),('owner-process-private.json',owner),('transport-child-private.json',child),('transport-terminal-private.json',term)]:simple_save(root/name,value)
        assert h.terminal_job(root)[0]['returncode']==0;passed('terminal_exact_input_same_owner_and_ssh_child')
        simple_save(root/'owner-process-private.json',dict(owner,startticks=999))
        reject('terminal_local_owner_birth_mismatch_rejected',lambda:h.terminal_job(root))
        simple_save(root/'owner-process-private.json',owner);simple_save(root/'transport-terminal-private.json',dict(term,terminal=False))
        reject('terminal_absence_or_result_label_cannot_replace_wait',lambda:h.terminal_job(root))

        # Saved original launch must be terminal0 and must prove this exact
        # supervisor/action/request, even if the later fetch child succeeds.
        root=temp/'launch-proof';root.mkdir();(root/'launch-job-private').mkdir();req=request();raw=encode(req)
        parent=dict(transaction_id=req['transaction_id'],boot_id=req['identity']['boot_id'],request_sha256=sha(raw),pid=810,start_ticks=None,argv=['supervisor'])
        intent=dict(stdin_sha256=sha(code),request_sha256=sha(raw),argv=argv)
        simple_save(root/'launch-intent-private.json',intent)
        job=dict(action='launch',stdin_sha256=sha(code),argv=argv);simple_save(root/'launch-job-private/job-private.json',job)
        response=dict(files={'launch-receipt-private.json':dict(base64=base64.b64encode(encode(parent)).decode())})
        launched=dict(transaction_id=req['transaction_id'],request_sha256=sha(raw),launched=True,supervisor_receipt=parent)
        with patch.object(h,'terminal_job',lambda p:(dict(returncode=0),launched)):assert h.review_launch_transport(root,req,raw,response)['original_launch_transport_terminal'];passed('original_launch_terminal0_same_supervisor')
        with patch.object(h,'terminal_job',lambda p:(dict(returncode=1),launched)):reject('original_launch_nonzero_not_promoted',lambda:h.review_launch_transport(root,req,raw,response))
        for name,changed in [('request',dict(launched,request_sha256='f'*64)),('supervisor',dict(launched,supervisor_receipt=dict(parent,pid=999))),('malformed',{})]:
            with patch.object(h,'terminal_job',lambda p,v=changed:(dict(returncode=0),v)):reject('original_launch_'+name+'_not_promoted',lambda:h.review_launch_transport(root,req,raw,response))
        simple_save(root/'launch-job-private/job-private.json',dict(job,action='fetch'))
        with patch.object(h,'terminal_job',lambda p:(dict(returncode=0),launched)):reject('original_launch_action_not_promoted',lambda:h.review_launch_transport(root,req,raw,response))

        # Execute fetch reviewer with real old-file/notes identities. Passed-like
        # labels without original child receipts retain raw but cannot qualify.
        req=request();raw=encode(req);tx=req['transaction_id'];base='/root/charging-management-20261023/'+tx
        wa=['python3','-B',base+'/restore-worker.py','--execute-rollback'];sa=['python3','-B',base+'/rollback-supervisor.py','--execute-supervisor']
        common=dict(transaction_id=tx,boot_id=req['identity']['boot_id'],request_sha256=sha(raw))
        worker=dict(transaction_id=tx,boot_id=req['identity']['boot_id'],pid=820,start_ticks=100,argv=wa,worker_sha256=sha(worker_raw))
        launch=dict(common,supervisor_pid=810,pid=820,start_ticks=100,argv=wa);end=dict(common,supervisor_pid=810,pid=820,argv=wa,terminal=True,returncode=0)
        sup=dict(common,pid=810,start_ticks=90,argv=sa);supend=dict(sup,terminal=True,worker_pid=820,worker_returncode=0,returncode=0)
        parent=dict(common,pid=810,start_ticks=90,argv=sa)
        value=dict(transaction_id=tx,profile=req['profile'],terminal=True,restored=True,status='staged_original/runtime_pending',runtime_pending=True,
            disk_state='all_original_fsynced',stop_verified=True,primary_error=None,unknown_write_state=False,actual_resident_notes=w.expected_profile(req)[1],
            final_files={name:dict(sha256=digest,mode='0o600',classification='original') for name,digest in w.OLD_FILES.items()},temporary_files={name:dict(state='absent') for name in w.ORDER})
        raws={name:encode(v) for name,v in [('process-private.json',worker),('worker-launch-receipt-private.json',launch),('worker-terminal-private.json',end),('supervisor-process-private.json',sup),('supervisor-terminal-private.json',supend),('launch-receipt-private.json',parent),('result.json',value)]}
        def fetch_response():return dict(transaction_id=tx,request_sha256=sha(raw),worker_terminal_verified=True,worker_terminal=end,worker_result=value,
            process=dict(state='absent'),supervisor_process=dict(state='source_boot_ended'),files={name:dict(base64=base64.b64encode(v).decode(),sha256=sha(v),bytes=len(v)) for name,v in raws.items()})
        for index,kind in enumerate(('good','no_terminal','bad_return','raw_result_label')):
            out=temp/('fetch-'+str(index));out.mkdir();response=fetch_response()
            if kind=='no_terminal':response['files'].pop('worker-terminal-private.json')
            if kind=='bad_return':
                bad=dict(end,returncode=2);response['worker_terminal']=bad
                for name,v in [('worker-terminal-private.json',bad),('supervisor-terminal-private.json',dict(supend,worker_returncode=2))]:
                    b=encode(v);response['files'][name]=dict(base64=base64.b64encode(b).decode(),sha256=sha(b),bytes=len(b))
            if kind=='raw_result_label':response['worker_terminal_verified']=False
            result=h.accept_fetch(out,req,raw,response)
            assert result['rollback_staged_original'] is (kind=='good') and result['runtime_validation_accepted'] is False
            assert (out/'raw/result.json').read_bytes()==encode(value)
            passed('fetch_'+kind+'_actual_chain_or_unqualified_raw')

    result=dict(passed=True,case_count=len(cases),cases=cases,
        tested_files={name:sha((HERE/name).read_bytes()) for name in ('host.py','remote.py','supervisor.py','test-wire.py')},
        actual_new_functions=['bind','ssh_owner','start_job','terminal_job','review_launch_transport','accept_fetch','remote.execute','supervisor.supervise'],
        fake_boundaries=['authenticated saved source/current proof except missing-actual-evidence refusal','Linux device filesystem, BOOTTIME, uid and identity','Popen/process interfaces; no real transport child','receipt publication errors'],
        old_suites_rerun=False,runtime_material_or_lease_generated=False,device_or_transport_accessed=False)
    (HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__=='__main__':main()
