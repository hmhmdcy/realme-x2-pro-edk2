"""New adapter boundaries only. Existing source/action authentication is fake."""
from pathlib import Path
from unittest.mock import patch
import base64,copy,hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encode=lambda value:(json.dumps(value,indent=2)+'\n').encode()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    b=load(HERE/'bind.py','actual_rollback_adapter');b.source_check()
    worker=load(b.ROLLBACK/'restore-worker.py','actual_frozen_rollback_validator')
    source=dict(boot_id='00000000-0000-4000-8000-000000000502',version=worker.VERSION,
        serial_sha256='1'*64,compatible_sha256='2'*64,rootfs_sha256='3'*64)
    projection=dict(transaction_id='usb-irq-protection-stage-synthetic001',request_sha256='4'*64,result_sha256='5'*64,
        host_binding_sha256='6'*64,worker_sha256=worker.STAGE_WORKER,supervisor_sha256=worker.STAGE_SUPERVISOR,evidence={})
    argv=b.transport_argv();cases=[]
    def rejected(name,operation):
        try:operation()
        except (ValueError,RuntimeError,AssertionError,FileNotFoundError,KeyError):cases.append(name)
        else:raise AssertionError(name)
    def fixture(profile):
        saved=dict(profile=profile,source_identity=copy.deepcopy(source),source_stage=copy.deepcopy(projection),activation=None)
        current=dict(identity=copy.deepcopy(source),release=worker.RELEASE,machine='aarch64',taint='0',
            boot=dict(bytes=100663296,sha256=worker.BOOT),logdump=dict(bytes=67108864,sha256=worker.LOGDUMP),
            notes=copy.deepcopy(worker.OLD_NOTES),module_states={n:'live' for n in worker.OLD_NOTES})
        if profile!=worker.PROFILES[0]:
            current['identity']['boot_id']='00000000-0000-4000-8000-000000000504'
            current['boot']['sha256']=worker.IRQ_BOOT if profile==worker.PROFILES[1] else worker.BOOT
            current['notes']=copy.deepcopy(worker.NEW_NOTES)
            saved['activation']=dict(schema='samurai-irq-rollback-saved-activation-binding-v1',activation_transaction_id='usb-irq-protection-activate-synthetic001',
                **{key:'7'*64 for key in ('context_sha256','guard_sha256','flash_request_sha256','flash_result_sha256','reboot_request_sha256','reboot_result_sha256')},
                flash_claimed_ns=1,reboot_claimed_ns=2,boot_sha256=current['boot']['sha256'],retained_logdump_sha256=worker.LOGDUMP,
                action_pair=['flash-candidate','reboot-candidate'] if profile==worker.PROFILES[1] else ['rollback-original','reboot-original'])
        request=b.probe_request(saved,b.PEER)
        report=dict(schema=request['schema'],request=request,identity_before=copy.deepcopy(current['identity']),current=current,
            identity_after=copy.deepcopy(current['identity']),started_boottime_ns=1,ended_boottime_ns=2)
        payload=('PROBE_REQUEST='+repr(request)+'\n').encode()+(HERE/'current-probe.py').read_bytes()
        return saved,report,payload
    with tempfile.TemporaryDirectory(prefix='rollback-adapter-synthetic-') as temp:
        temp=Path(temp);probe=temp/'probe';probe.mkdir()
        def publish(report,payload):
            stdout,stderr=encode(report),b''
            child=dict(pid=907,start_ticks=1234,argv=argv,stdin_sha256=sha(payload))
            terminal=dict(child,terminal=True,returncode=0,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),primary_error=None,cleanup_errors=[])
            for name,raw in [('executed-device-source.py',payload),('stdout-private.json',stdout),('stderr-private.txt',stderr),
                             ('child-private.json',encode(child)),('terminal-private.json',encode(terminal))]:(probe/name).write_bytes(raw)
        for index,profile in enumerate(worker.PROFILES):
            saved,report,payload=fixture(profile);publish(report,payload)
            with patch.object(b,'review_sources',return_value=saved):
                result=b.bind(temp/('bound-'+str(index)),'usb-irq-protection-rollback-synthetic00'+str(index),profile,temp,temp,probe)
            request=json.loads((temp/('bound-'+str(index))/'request-private.json').read_bytes())
            assert request['identity']==report['current']['identity'] and request['source_identity']==source
            if index:assert request['identity']['boot_id']!=source['boot_id']
            assert result['worker_launched'] is False and result['lease_written'] is False
            cases.append('actual binder/current profile accepts explicit '+profile+' without whole-postboot passed')
        profile=worker.PROFILES[1];saved,report,payload=fixture(profile)
        with patch.object(b,'review_sources',return_value=saved):
            def reject_current(name,changed):
                publish(changed,payload);out=temp/'must-not-exist'
                rejected(name,lambda:b.bind(out,'usb-irq-protection-rollback-syntheticbad',profile,temp,temp,probe))
                assert not out.exists()
            changed=copy.deepcopy(report);changed['current']['notes']=worker.OLD_NOTES
            reject_current('wrong actual live notes refused before mkdir',changed)
            changed=copy.deepcopy(report);changed['current']['boot']['sha256']=worker.BOOT
            reject_current('wrong actual complete carrier refused before mkdir',changed)
            changed=copy.deepcopy(report)
            for key in ('identity_before','identity_after'):changed[key]['boot_id']=source['boot_id']
            changed['current']['identity']['boot_id']=source['boot_id']
            reject_current('new identity is not silently filled from original adoption/source UUID',changed)
            changed=copy.deepcopy(report);changed['identity_after']['boot_id']='00000000-0000-4000-8000-000000000999'
            reject_current('identity changed during full current read refused',changed)
            changed=copy.deepcopy(report);changed['request']['saved_source_binding_sha256']='f'*64
            reject_current('probe source/profile proof binding mismatch refused',changed)
            publish(report,payload)
            child=json.loads((probe/'child-private.json').read_bytes());child.pop('stdin_sha256');(probe/'child-private.json').write_bytes(encode(child))
            rejected('actual reused R2 receipt gate refuses absent exact-input binding',lambda:b.review_current(profile,temp,temp,probe))
            publish(report,payload)
            terminal=json.loads((probe/'terminal-private.json').read_bytes());terminal['returncode']=255;(probe/'terminal-private.json').write_bytes(encode(terminal))
            rejected('original strict-key child nonzero cannot produce request',lambda:b.review_current(profile,temp,temp,probe))
            publish(report,payload)
            rejected('stage transaction cannot be reused as rollback name',lambda:b.bind(temp/'wrong-name','usb-irq-protection-stage-synthetic001',profile,temp,temp,probe))
            assert not (temp/'wrong-name').exists()
        rejected('missing actual saved source/profile material refuses before output mkdir',
            lambda:b.bind(temp/'missing-real','usb-irq-protection-rollback-missingactual',profile,temp/'missing-stage',temp/'missing-fetch',probe))
        assert not (temp/'missing-real').exists()
    result=dict(passed=True,count=len(cases),cases=cases,actual_new_adapter_functions=True,
        actual_reused_R2_transport_receipt_auth=True,actual_worker_unpack_and_profile_validation=True,
        existing_saved_stage_and_activation_authentication_boundaries_fake=True,
        synthetic_test_bind_artifacts_only=True,actual_runtime_request_guard_or_lease_generated=False,
        device_SSH_USB_SDK_build_Git=False,old_21_6_20_suites_rerun=False,
        files={name:sha((HERE/name).read_bytes()) for name in ('bind.py','current-probe.py','test-bind.py')})
    with (HERE/'test-result.json').open('x') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,count=len(cases))))


if __name__=='__main__':main()
