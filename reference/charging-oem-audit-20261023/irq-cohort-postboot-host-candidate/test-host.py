"""New host authentication boundaries only; no old suite or real future identity."""
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import base64
import copy
import contextlib
import hashlib
import importlib.util
import io
import json
import shlex
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value, indent=2) + '\n').encode()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    host = load(HERE / 'host.py', 'actual_irq_postboot_host_tests')
    # Windows lacks Linux fcntl. The actual frozen module's pure checks/audit
    # execute; no ioctl/collect/main is called by this test.
    with patch.dict(sys.modules, {'fcntl': ModuleType('fcntl')}):
        device = load(host.DEVICE / 'device.py', 'actual_irq_postboot_device_tests')
    old = load(HERE.parent / 'image502-postboot-readonly/fixture.py', 'saved_502_fixture_only')
    old.ORIGINAL = Path('E:/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/postboot-r1-04-private/stdout-private.json')
    raw = old.facts()
    cohort = json.loads((REF / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/cohort-manifest.json').read_bytes())
    manifest = json.loads((REF / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/manifest.json').read_bytes())
    raw['boot_partition']['sha256'] = host.IRQ_BOOT
    raw['manifest']['sha256'] = device.COHORT_MANIFEST
    raw['manifest_text'] = json.dumps(manifest)
    for name, info in cohort['modules'].items():
        raw['installed_files'][manifest['modules'][name]['target']]['sha256'] = info['new']['sha256']
        raw['charging_modules'][name].update(sha256=info['new']['sha256'], disk_note_sha256=info['new']['resident_note_sha256'],
             loaded_note_sha256=info['new']['resident_note_sha256'], loaded_note_matches_disk=True)
    raw['started_boottime_ns'], raw['ended_boottime_ns'] = 1, 100
    location = '/sys/devices/platform/soc@0/c440000.spmi/spmi-0/0-02/1300.usb-input'
    interrupt_text = '           CPU0       CPU1\n 47: 0 0 pmic_arb 135940 Edge usbin-plugin\n 48: 0 0 pmic_arb 135942 Edge usbin-src-change\n'
    def snapshot(start, end):
        return dict(started_boottime_ns=start, ended_boottime_ns=end, device=location,
            driver='samurai-usb-input', of_node=device.NODE, bound_providers=[location], proc_interrupts=interrupt_text,
            properties_b64={key:base64.b64encode(value).decode() for key,value in device.PROPERTIES.items()})
    raw['irq_before'], raw['irq_after'] = snapshot(2, 3), snapshot(98, 99)
    identity = raw['identity_before']
    stage_tx = 'usb-irq-protection-stage-fixture0001'
    activate_tx = 'usb-irq-protection-activate-fixture0001'
    guard = dict(transaction_id=activate_tx, boot_id=old.OLDBOOT, kernel_release=identity['uname']['release'],
        kernel_version=host.VERSION, rootfs_release_sha256=identity['rootfs']['sha256'],
        soc_serial_sha256=identity['serial_sha256'], compatible_sha256=sha(base64.b64decode(identity['compatible_b64'])))
    stage_result = dict(transaction_id=stage_tx, terminal=True, status='staged/runtime_pending', runtime_pending=True,
        disk_state='all_new_fsynced', stop_verified=True, old_manifest_sha256='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f',
        new_manifest_sha256=device.COHORT_MANIFEST)
    stage = dict(transaction_id=stage_tx, source_boot_id=old.OLDBOOT, stage_result=stage_result,
                 result_sha256=sha(encode(stage_result)))
    activation = dict(schema='samurai-usb-irq-protection-completed-activation-review-v1', guard=guard,
        activation_transaction_id=activate_tx, source_boot_id=old.OLDBOOT, context_sha256='a'*64, guard_sha256=sha(encode(guard)),
        partitions_written=['boot'], candidate_boot_sha256=host.IRQ_BOOT, retained_logdump_sha256=host.LOGDUMP,
        saved_activation_commands_verified=True, context={})
    pins = {'key_transport':dict(path=str(REF / 'kernel184/host.py'))}
    key = load(REF / 'kernel184/host.py', 'actual_original_key_tests')
    argv = [key.SSH, '-6', '-T', *key.OPTIONS, '-o', 'HostKeyAlias='+host.ALIAS, 'root@'+host.PEER, 'python3 -']
    cases = []
    def reject(name, operation):
        try:operation()
        except (ValueError, AssertionError, KeyError, FileNotFoundError):cases.append(dict(name=name, passed=True))
        else:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix='irq-host-synthetic-') as temp:
        temp = Path(temp)
        probe_dir = temp / 'probe'; probe_dir.mkdir()
        capture_dir = temp / 'capture'; capture_dir.mkdir()
        camera = Path('E:/edk2-samurai-out/kernel481/formal-expected-private.json')
        def publish(directory, payload, report, rc=0):
            stdout, stderr = encode(report), b''
            actual_argv = (host.transport_argv(host.PEER,collection=True) if directory==capture_dir else argv)
            child = dict(pid=701, start_ticks=891, argv=actual_argv)
            terminal = dict(child, terminal=True, returncode=rc, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
                            primary_error=None, cleanup_errors=[])
            for name, value in [('executed-device-source.py',payload), ('stdout-private.json',stdout),
                ('stderr-private.txt',stderr), ('child-private.json',encode(child)), ('terminal-private.json',encode(terminal))]:
                (directory/name).write_bytes(value)
        # Existing completed-activation and saved-stage reviews are the explicit
        # authenticated boundary here; this suite exercises new host glue,
        # exact strict-key Popen/source/output checks and actual device audit.
        with patch.object(host, 'completed', return_value=(activation,stage)), patch.object(host,'source_check',return_value=pins), patch.object(host,'device_module',return_value=device):
            probe_request = host.probe_request(activation,stage,host.PEER)
            probe_report = dict(schema=probe_request['schema'],request=probe_request,
                identity_before=copy.deepcopy(identity),identity_after=copy.deepcopy(identity),
                started_boottime_ns=1,ended_boottime_ns=2)
            probe_payload = host.probe_payload(temp/'nonexistent-context',host.PEER)
            publish(probe_dir,probe_payload,probe_report)
            verified = host.review_probe(temp/'context',probe_dir)
            assert verified['new_boot_id']==old.NEWBOOT
            request = host.make_request(temp/'context',camera,probe_dir)
            assert request['guard']['transaction_id']==stage_tx and request['activation_transaction_id']==activate_tx
            assert request['activation_guard']==guard and guard['transaction_id']==activate_tx
            cases.append(dict(name='real functions project stage identity without modifying activation guard; key probe new boot accepted',passed=True))
            payload = host.make_payload(request)
            command = host.transport_argv(host.PEER,collection=True)[-1]
            with patch.object(device,'collect',side_effect=lambda req,target:target.update(copy.deepcopy(raw))), contextlib.redirect_stdout(io.StringIO()) as printed:
                assert device.main(shlex.split(command)[3:],request)==0
            assert json.loads(printed.getvalue())['result']['passed'] is True
            cases.append(dict(name='collection-specific argv reaches actual frozen main execute path with only IO boundary fake',passed=True))
            report = dict(schema=request['schema'],transaction_id=stage_tx,context_sha256=request['context_sha256'],
                guard_sha256=request['guard_sha256'],raw=raw,result=device.audit(raw,request))
            assert report['result']['passed']
            publish(capture_dir,payload,report)
            assert host.evaluate_response(temp/'context',camera,probe_dir,capture_dir)['passed']
            cases.append(dict(name='saved collector whole raw reaudited through actual frozen ten-check audit',passed=True))
            child=read_json(capture_dir/'child-private.json');child['argv']=argv
            (capture_dir/'child-private.json').write_bytes(encode(child))
            reject('probe-only default command cannot stand in for actual collector execution',lambda:host.evaluate_response(temp/'context',camera,probe_dir,capture_dir))
            publish(capture_dir,payload,report)
            wrong=copy.deepcopy(probe_report);wrong['identity_before']['boot_id']=old.OLDBOOT
            publish(probe_dir,probe_payload,wrong);reject('old boot cannot bind a request',lambda:host.make_request(temp/'context',camera,probe_dir))
            publish(probe_dir,probe_payload,probe_report)
            wrong=copy.deepcopy(probe_report);wrong['identity_after']['boot_id']='00000000-0000-0000-0000-000000000999'
            publish(probe_dir,probe_payload,wrong);reject('boot changes during probe',lambda:host.review_probe(temp/'context',probe_dir))
            publish(probe_dir,probe_payload,probe_report)
            term=read_json(probe_dir/'terminal-private.json');term['returncode']=False
            (probe_dir/'terminal-private.json').write_bytes(encode(term));reject('boolean terminal is not Popen integer rc',lambda:host.review_probe(temp/'context',probe_dir))
            publish(probe_dir,probe_payload,probe_report)
            child=read_json(probe_dir/'child-private.json');child['argv'][-2]='root@169.254.42.1'
            (probe_dir/'child-private.json').write_bytes(encode(child));reject('endpoint fallback is not authenticated original new endpoint',lambda:host.review_probe(temp/'context',probe_dir))
            publish(probe_dir,probe_payload,probe_report)
            term=read_json(probe_dir/'terminal-private.json');term['start_ticks']+=1
            (probe_dir/'terminal-private.json').write_bytes(encode(term));reject('terminal belongs to different process birth',lambda:host.review_probe(temp/'context',probe_dir))
            publish(probe_dir,probe_payload,probe_report)
            (probe_dir/'executed-device-source.py').write_bytes(probe_payload+b'\n#not actual\n')
            reject('executed probe source differs',lambda:host.review_probe(temp/'context',probe_dir));publish(probe_dir,probe_payload,probe_report)
            wrong=copy.deepcopy(probe_report);wrong['request']['guard_sha256']='f'*64
            publish(probe_dir,probe_payload,wrong);reject('probe does not bind actual activation raw guard',lambda:host.review_probe(temp/'context',probe_dir));publish(probe_dir,probe_payload,probe_report)
            wrong=copy.deepcopy(report);wrong['raw']['boot_partition']['sha256']='0'*64
            publish(capture_dir,payload,wrong);reject('forged passed result differs from actual raw audit',lambda:host.evaluate_response(temp/'context',camera,probe_dir,capture_dir))
            wrong['result']=device.audit(wrong['raw'],request);publish(capture_dir,payload,wrong,1)
            assert not host.evaluate_response(temp/'context',camera,probe_dir,capture_dir)['passed']
            cases.append(dict(name='ordinary failed raw audit retained as failed',passed=True))
            wrong=copy.deepcopy(report);wrong['raw']['identity_before']['boot_id']='00000000-0000-0000-0000-000000000999'
            wrong['raw']['identity_after']['boot_id']=wrong['raw']['identity_before']['boot_id'];wrong['result']=device.audit(wrong['raw'],request)
            assert wrong['result']['passed'];publish(capture_dir,payload,wrong)
            reject('otherwise healthy different post-probe boot is refused',lambda:host.evaluate_response(temp/'context',camera,probe_dir,capture_dir))
            wrong=copy.deepcopy(report);wrong['raw']={};wrong['result']=dict(passed=False,read_only=True,collection_error='OSError',message='synthetic')
            publish(capture_dir,payload,wrong,1)
            assert not host.evaluate_response(temp/'context',camera,probe_dir,capture_dir)['passed']
            cases.append(dict(name='collector exception partial raw retained without accepting complete audit',passed=True))
            reject('missing real probe denies before output mkdir',lambda:host.bind(temp/'must-not-exist',temp/'context',camera,temp/'missing'))
            assert not (temp/'must-not-exist').exists()
            reject('unobserved endpoint is refused',lambda:host.probe_payload(temp/'context','169.254.42.1'))
        # No source/context files exist in the next call: the actual entry must
        # reject before mkdir, independently of all synthetic good fixtures.
        reject('missing real completed activation rejects before mkdir',lambda:host.bind(temp/'real-must-not-exist',temp/'missing-context',camera,temp/'missing-probe'))
        assert not (temp/'real-must-not-exist').exists()
    result=dict(passed=True,count=len(cases),cases=cases,
        actual_new_host_functions=True,actual_frozen_device_audit=True,
        existing_stage_and_completed_activation_boundaries_fake=True,
        synthetic_fixture_only=True,real_request_or_guard_generated=False,device_or_transport_accessed=False,
        old_suites_rerun=False,files={n:sha((HERE/n).read_bytes()) for n in ('host.py','identity-probe.py','test-host.py')})
    (HERE/'host-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,count=len(cases))))


def read_json(path):return json.loads(Path(path).read_bytes())


if __name__=='__main__':main()
