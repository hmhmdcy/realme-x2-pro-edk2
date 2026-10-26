"""Read only saved source stage and selected boot-action proofs; never transport."""
from pathlib import Path
import hashlib
import importlib.util
import json
HERE=Path(__file__).resolve().parent
PROFILES=('staged_same_boot_old_resident','booted_irq_new_resident','booted_original_new_resident')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(value,message):
    if not value:raise ValueError(message)


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def source_check():
    proof=HERE.parent/'irq-cohort-postboot-host-candidate/stage-proof.py'
    completion=HERE.parent/'usb-irq-protection-fastboot-candidate/completion-proof.py'
    delivery=HERE.parent/'usb-irq-protection-fastboot-candidate/delivery.json'
    need(sha(proof)=='85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093','frozen original stage reviewer')
    need(sha(completion)=='d4a7b29c3f5978c1254c4b7c40376fbf12453057d4ba8cc98cbb4ef7a952be00'
         and sha(delivery)=='ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41','frozen original boot reviewer')
    return load(proof,'rollback_original_stage'),load(completion,'rollback_original_completion')


def review_profile_sources(profile,stage_directory,stage_fetch_directory,context_path=None):
    need(profile in PROFILES,'explicit supported profile')
    stage_module,completion=source_check()
    stage=stage_module.review_stage(stage_directory,stage_fetch_directory)
    projection=stage_module.guard_stage_fields(stage)
    activation=None;selected=None
    if profile==PROFILES[0]:
        need(context_path is None,'same-boot profile does not consume an activation proof')
    else:
        need(context_path is not None,'actual original saved activation required')
        path=Path(context_path)
        if profile==PROFILES[1]:
            actual=completion.review_completed_activation(path)
            context,guard=actual['context'],actual['guard'];flash,reboot=actual['flash'],actual['reboot']
            boot=actual['candidate_boot_sha256'];logdump=actual['retained_logdump_sha256']
        else:
            # Candidate-completion deliberately rejects a later original boot
            # restoration. Review its exact selected originals instead.
            operator=completion.source_module();context=operator.validate_context(path)
            base=path.resolve().parent/'fastboot-operator';operator.prior_terminal(base,'inspect')
            flash=completion.review_action(operator,path,context,'rollback-original')
            reboot=completion.review_action(operator,path,context,'reboot-original')
            guard=json.loads(operator.reference_file(path.resolve().parent,context['files']['guard']).read_bytes())
            boot=operator.ORIGINAL_BOOT;logdump=operator.LOGDUMP502
            for name in ('flash-candidate','reboot-candidate'):
                if (base/name).exists():
                    prior=json.loads((base/name/'request-private.json').read_bytes())
                    need(prior['claimed_ns']<flash['claimed_ns'],'later candidate action invalidates original-boot profile')
        need(guard['stage']==projection and guard['boot_id']==stage['source_boot_id'],'selected activation belongs to original source stage')
        identity=stage['identity']
        need(guard['kernel_version']==identity['version'] and guard['soc_serial_sha256']==identity['serial_sha256']
             and guard['compatible_sha256']==identity['compatible_sha256'] and guard['rootfs_release_sha256']==identity['rootfs_sha256'],
             'activation/source board differs')
        need(flash['claimed_ns']<reboot['claimed_ns'] and flash['all_original_children_terminal0'] is True
             and reboot['all_original_children_terminal0'] is True,'actual selected Popen write/reboot order')
        activation=dict(schema='samurai-irq-rollback-saved-activation-binding-v1',activation_transaction_id=context['transaction_id'],
            context_sha256=sha(path),guard_sha256=context['guard_sha256'],flash_request_sha256=flash['request_sha256'],
            flash_result_sha256=flash['result_sha256'],reboot_request_sha256=reboot['request_sha256'],reboot_result_sha256=reboot['result_sha256'],
            flash_claimed_ns=flash['claimed_ns'],reboot_claimed_ns=reboot['claimed_ns'],boot_sha256=boot,retained_logdump_sha256=logdump,
            action_pair=['flash-candidate','reboot-candidate'] if profile==PROFILES[1] else ['rollback-original','reboot-original'])
        selected=dict(flash=flash,reboot=reboot)
    return dict(schema='samurai-irq-rollback-saved-source-review-v1',profile=profile,
        source_identity=stage['identity'],source_stage=projection,activation=activation,
        saved_selected_actions=selected,source_stage_terminal_authenticated=True,
        current_identity_or_protection_or_stopped_verified=False,
        runtime_request_generated=False,device_or_transport_accessed=False)


if __name__=='__main__':
    source_check();print(json.dumps(dict(source_only=True,actual_source_stage_reviewed=False,runtime_request_generated=False,device_or_transport_accessed=False)))
