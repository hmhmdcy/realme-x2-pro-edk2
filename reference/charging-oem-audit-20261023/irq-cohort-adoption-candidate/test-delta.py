"""New adoption boundaries only. All runtime identities/IO are synthetic in tempdirs."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,io,json,os,subprocess,sys,tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('irq_adoption_delta',HERE/'adopt.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=m.sha
encode=lambda x:(json.dumps(x,indent=2)+'\n').encode()

def main():
    cases=[]
    def passed(name):cases.append({'name':name,'passed':True})
    def reject(name,fn):
        try:fn()
        except (ValueError,AssertionError,FileExistsError,OSError,KeyError):passed(name)
        else:raise AssertionError(name)
    m.sources();passed('exact frozen sources and actual collector prefix parse')
    with tempfile.TemporaryDirectory(prefix='irq-adoption-synthetic-') as temp:
        root=Path(temp);tx='usb-irq-protection-activate-fixture0001';folder=root/tx;folder.mkdir()
        context=folder/'context-private.json';context.write_bytes(b'{}\n')
        capture=folder/'capture';capture.mkdir()
        oldboot='11111111-1111-4111-8111-111111111111';newboot='22222222-2222-4222-8222-222222222222'
        ident={'boot_id':newboot,'uname':{'release':'7.3.0-rc6-rmx1931-samurai-k363+',
            'version':'#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'},'rootfs':{'sha256':'1'*64},
            'serial_sha256':'2'*64,'compatible_b64':base64.b64encode(b'realme,rmx1931\0').decode()}
        previous={'guard_path':'/var/lib/samurai/source502/boot-id-private.txt','original_key_verified':True,
            'baseline481_verified':True,'Image502_verified':True,'charging_manifest_sha256':'320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f',
            'candidate_boot_sha256':'97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
            'candidate_logdump_sha256':'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1','postboot_raw_sha256':'3'*64}
        request={'activation_transaction_id':tx,'guard':{'transaction_id':'usb-irq-protection-stage-fixture0001'},
            'activation_guard':{'boot_id':oldboot,'adoption':{'guard_path':previous['guard_path'],'postboot_raw_sha256':'3'*64}},
            'new_boot_id':newboot,'new_endpoint':'fe80::62:bcff:fe28:a101%29','context_sha256':'4'*64,'guard_sha256':'5'*64}
        raw={'identity_before':ident,'identity_after':copy.deepcopy(ident),
            'boot_partition':{'sha256':'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'},
            'logdump_partition':{'sha256':previous['candidate_logdump_sha256']},
            'manifest':{'sha256':'5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'}}
        report={'raw':raw};report_path=capture/'stdout-private.json';report_path.write_bytes(encode(report))
        evaluated={'passed':True,'transport_returncode':0,'hardware_writes':0,'checks':['ok']*10,'errors':[]}
        # The previously tested host R2 is an explicit authenticated boundary.
        # This suite tests only this new caller's additional fields and writes.
        host=SimpleNamespace(evaluate_response=lambda *a:copy.deepcopy(evaluated),
            make_request=lambda *a:copy.deepcopy(request),transport_argv=lambda endpoint:['synthetic-owned-child',endpoint])
        with patch.object(m,'host_module',return_value=host):
            adoption,sources=m.review(context,'camera','probe',capture)
            assert adoption['boot']==newboot and adoption['old_boot']==oldboot
            assert adoption['postboot_raw_sha256']==sha(report_path.read_bytes())
            passed('actual new adoption descriptor retains original authenticated request and raw bytes')
            evaluated['passed']=False
            reject('unpassed actual host result refused',lambda:m.review(context,'camera','probe',capture));evaluated['passed']=True
            original=report_path.read_bytes()
            for name,change in [('same source UUID',lambda r:r['raw']['identity_before'].update(boot_id=oldboot)),
                                ('old boot carrier',lambda r:r['raw']['boot_partition'].update(sha256=previous['candidate_boot_sha256'])),
                                ('old manifest',lambda r:r['raw']['manifest'].update(sha256=previous['charging_manifest_sha256']))]:
                value=json.loads(original);change(value);report_path.write_bytes(encode(value))
                reject(name+' refused',lambda:m.review(context,'camera','probe',capture))
            report_path.write_bytes(original)
        m.check_previous(previous,adoption);passed('source502 pointer accepted only as retained predecessor')
        bad=copy.deepcopy(previous);bad['Image502_verified']=False
        reject('old501 pointer refused',lambda:m.check_previous(bad,adoption))
        bad=copy.deepcopy(previous);bad['postboot_raw_sha256']='f'*64
        reject('mixed source postboot refused',lambda:m.check_previous(bad,adoption))
        code=m.payload(adoption,sources);ast.parse(code)
        assert code.count(b'print(json.dumps(adopt_current_irq_boot(ADOPTION))')==1
        passed('exact collector prefix plus sole adoption call parse without collector main')
        tree=ast.parse((HERE/'adopt-device-tail.inc').read_bytes())
        functions=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[])
        remote_root=root/'remote';remote_root.mkdir();oldguard=remote_root/'old-guard';oldguard.write_text(oldboot+'\n')
        remote=copy.deepcopy(adoption);remote['guard']=str(remote_root/(tx+'-adopted')/'boot-id-private.txt')
        state={'fail':False,'boot':newboot}
        def collect(req,out):
            assert req==request
            out.update(identity_before={**copy.deepcopy(ident),'boot_id':state['boot']},
                       identity_after={**copy.deepcopy(ident),'boot_id':state['boot']})
        env=dict(Path=Path,re=__import__('re'),os=os,json=json,hashlib=hashlib,GUARD_ROOT=remote_root,
            collect=collect,audit=lambda *a:{'passed':not state['fail'],'errors':['synthetic'] if state['fail'] else [],'hardware_writes':0})
        exec(compile(functions,'actual-adopt-device-tail','exec'),env)
        state['fail']=True
        reject('failed fresh raw audit creates no guard directory',lambda:env['adopt_current_irq_boot'](remote))
        assert not Path(remote['guard']).parent.exists();state['fail']=False;state['boot']=oldboot
        reject('fresh boot changed creates no guard directory',lambda:env['adopt_current_irq_boot'](remote))
        state['boot']=newboot;reply=env['adopt_current_irq_boot'](remote)
        assert reply['guard_sha256']==sha((newboot+'\n').encode()) and oldguard.read_text()==oldboot+'\n'
        assert reply['fresh_validation_sha256']==sha((Path(remote['guard']).parent/'fresh-validation-private.json').read_bytes())
        passed('fresh proof and UUID guard fsynced/readback with old guard retained')
        reject('existing complete or partial adoption directory never reopened',lambda:env['adopt_current_irq_boot'](remote))
        base=root/'host-private';base.mkdir();pointer=base/'boot-adoption-private.json';pointer.write_bytes(encode(previous))
        output=base/'publish';output.mkdir();(output/'boot-adoption-before-irq-private.json').write_bytes(pointer.read_bytes())
        hostreply={**reply,'guard':adoption['guard']}
        with patch.object(m,'BASE',base):
            result=m.publish(output,adoption,hostreply)
            assert json.loads(pointer.read_bytes())==result and result['USB_IRQ_protection_verified'] is True
            assert result['candidate_boot_sha256']==adoption['candidate_boot_sha256']
            passed('new pointer published only after actual fresh reply and old pointer comparison')
            reject('changed global pointer refuses publish',lambda:m.publish(output,adoption,hostreply))
        class Child:
            pid=710;returncode=None
            def __init__(self,argv,**kw):self.stdin=io.BytesIO();self.out=kw['stdout'];self.waited=0;self.sent=None;self.argv=argv
            def communicate(self,input):
                self.sent=input
                if state.get('send_error'):raise OSError('synthetic partial send')
                self.out.write(encode({'synthetic_reply':True}));self.stdin.close();self.returncode=0
            def wait(self):self.waited+=1;self.returncode=0;return 0
        children=[]
        def popen(argv,**kw):
            c=Child(argv,**kw);children.append(c);return c
        def identity(c,argv):return dict(pid=c.pid,start_ticks=123,argv=argv,observed_argv=['synthetic-Windows-interop'])
        with patch.object(m.subprocess,'Popen',side_effect=popen),patch.object(m,'process_identity',side_effect=identity):
            out=root/'transfer-ok';out.mkdir();assert m.transfer(out,b'original-input',host,adoption['endpoint'])=={'synthetic_reply':True}
            terminal=json.loads((out/'adopt-terminal-private.json').read_bytes())
            assert children[-1].waited==1 and terminal['stdin_sha256']==sha(b'original-input') and terminal['terminal'] is True
            passed('one original child and exact stdin retained through real wait boundary')
            real_save=m.save
            def fail_receipt(path,value):
                if Path(path).name=='adopt-child-private.json':raise OSError('synthetic receipt failure')
                real_save(path,value)
            out=root/'receipt-fail';out.mkdir()
            with patch.object(m,'save',side_effect=fail_receipt):
                reject('receipt failure closes original stdin and waits without sending',lambda:m.transfer(out,b'original-input',host,adoption['endpoint']))
            assert children[-1].sent is None and children[-1].stdin.closed and children[-1].waited==1
            out=root/'send-fail';out.mkdir();state['send_error']=True
            reject('partial send failure waits same child and retains failed terminal',lambda:m.transfer(out,b'original-input',host,adoption['endpoint']))
            assert children[-1].stdin.closed and children[-1].waited==1
            assert json.loads((out/'adopt-terminal-private.json').read_bytes())['primary_error'] is not None
        # Harmless local process tests /proc identity on Linux; never SSH/USB.
        argv=[sys.executable,'-c','import sys; sys.stdin.buffer.read()']
        child=subprocess.Popen(argv,stdin=subprocess.PIPE)
        try:
            actual=m.process_identity(child,argv);assert actual['pid']==child.pid and actual['start_ticks']>0
        finally:child.stdin.close();assert child.wait()==0
        passed('actual owned local child birth/argv capture before input')
    result={'passed':True,'new_cases':len(cases),'cases':cases,
        'boundaries':'authenticated host R2 and device collect/audit are explicit fakes; new filesystem/transaction functions actual',
        'prior_host_device_operator_suites_rerun':False,'actual_endpoint_guard_request_created':False,
        'device_SSH_USB_SDK_used':False}
    (HERE/'test-result.json').write_bytes(encode(result));print(json.dumps({'passed':True,'new_cases':len(cases)}))

if __name__=='__main__':main()
