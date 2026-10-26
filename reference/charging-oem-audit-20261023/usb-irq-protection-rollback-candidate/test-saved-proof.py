"""Only new pure profile-selection glue; original proof/authentication edges fake."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    spec=importlib.util.spec_from_file_location('actual_rollback_saved_proof',HERE/'saved-proof.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    stages=dict(transaction_id='usb-irq-protection-stage-synthetic001')
    identity=dict(boot_id='00000000-0000-4000-8000-000000000502',version='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',
                  serial_sha256='1'*64,compatible_sha256='2'*64,rootfs_sha256='3'*64)
    stage=dict(identity=identity,source_boot_id=identity['boot_id'])
    stage_module=SimpleNamespace(review_stage=lambda *args:stage,guard_stage_fields=lambda result:stages)
    flash=dict(request_sha256='4'*64,result_sha256='5'*64,claimed_ns=10,all_original_children_terminal0=True)
    reboot=dict(request_sha256='6'*64,result_sha256='7'*64,claimed_ns=20,all_original_children_terminal0=True)
    boot='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
    irq='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
    logdump='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
    cases=[];calls=[]
    def rejected(name,operation):
        try:operation()
        except ValueError:cases.append(name)
        else:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix='rollback-saved-proof-synthetic-') as temp:
        directory=Path(temp);context_path=directory/'host-context-private.json';guard_path=directory/'guard-private.json'
        guard=dict(stage=stages,boot_id=identity['boot_id'],kernel_version=identity['version'],soc_serial_sha256=identity['serial_sha256'],
                   compatible_sha256=identity['compatible_sha256'],rootfs_release_sha256=identity['rootfs_sha256'])
        guard_path.write_text(json.dumps(guard));context=dict(transaction_id='usb-irq-protection-activate-synthetic001',guard_sha256=sha(guard_path.read_bytes()),files={'guard':{}})
        context_path.write_text(json.dumps(context));base=directory/'fastboot-operator';base.mkdir()
        operator=SimpleNamespace(validate_context=lambda path:context,reference_file=lambda *args:guard_path,
            prior_terminal=lambda *args:calls.append('prior-terminal'),ORIGINAL_BOOT=boot,LOGDUMP502=logdump)
        def action(op,path,ctx,name):
            calls.append(name);return flash if name=='rollback-original' else reboot
        def completed(path):
            calls.append('review-completed-candidate')
            return dict(context=context,guard=guard,flash=flash,reboot=reboot,candidate_boot_sha256=irq,retained_logdump_sha256=logdump)
        completion=SimpleNamespace(source_module=lambda:operator,review_action=action,review_completed_activation=completed)
        with patch.object(m,'source_check',return_value=(stage_module,completion)):
            result=m.review_profile_sources(m.PROFILES[0],directory,directory)
            assert result['activation'] is None and not calls
            cases.append('same source boot profile consumes no activation and creates no current identity')
            result=m.review_profile_sources(m.PROFILES[1],directory,directory,context_path)
            assert result['activation']['action_pair']==['flash-candidate','reboot-candidate'] and calls==['review-completed-candidate']
            cases.append('candidate profile explicitly uses frozen completed-candidate reviewer')
            calls.clear();result=m.review_profile_sources(m.PROFILES[2],directory,directory,context_path)
            assert result['activation']['action_pair']==['rollback-original','reboot-original']
            assert result['activation']['boot_sha256']==boot and calls==['prior-terminal','rollback-original','reboot-original']
            cases.append('original boot profile authenticates original selected pair, never candidate completion')
            candidate=base/'flash-candidate';candidate.mkdir();(candidate/'request-private.json').write_text(json.dumps(dict(claimed_ns=11)))
            rejected('later opposing candidate action refuses original-boot completion',lambda:m.review_profile_sources(m.PROFILES[2],directory,directory,context_path))
            (candidate/'request-private.json').write_text(json.dumps(dict(claimed_ns=1)))
            rejected('same-boot profile refuses activation context substitution',lambda:m.review_profile_sources(m.PROFILES[0],directory,directory,context_path))
            old=reboot['claimed_ns'];reboot['claimed_ns']=9
            rejected('reboot before selected write refuses original completion',lambda:m.review_profile_sources(m.PROFILES[2],directory,directory,context_path))
            reboot['claimed_ns']=old
    result=dict(passed=True,count=len(cases),cases=cases,actual_pure_wrapper_functions=True,
        existing_stage_and_completion_authentication_boundaries_fake=True,old_proof_or_31_suites_rerun=False,
        synthetic_saved_material_only=True,runtime_request_or_guard_generated=False,device_or_transport_accessed=False,
        files={name:sha((HERE/name).read_bytes()) for name in ('saved-proof.py','test-saved-proof.py')})
    with (HERE/'saved-proof-test-result.json').open('x') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,count=len(cases))))


if __name__=='__main__':main()
