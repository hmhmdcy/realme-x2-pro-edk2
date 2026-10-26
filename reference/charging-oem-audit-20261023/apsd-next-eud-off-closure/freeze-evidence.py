"""Hash cached source/report inputs only; no imports of their entry points."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OEM='charging-oem-audit-20261023/'
SESSION='charging-session-20261023/'
files=[
 OEM+'apsd-input-backend-candidate/samurai-usb-input.c',
 OEM+'apsd-input-backend-candidate/samurai-apsd-input.inc',
 OEM+'apsd-input-backend-candidate/samurai-apsd-backend.h',
 OEM+'apsd-input-backend-candidate/samurai-usb-input-decode.h',
 SESSION+'apsd-session-owner-candidate/samurai-apsd-owner.c',
 SESSION+'apsd-session-owner-candidate/samurai-apsd-owner.h',
 SESSION+'apsd-session-owner-candidate/Kconfig.fragment',
 OEM+'pd5v-owner-context-r2/qcom_pmic_typec.c',
 OEM+'pd5v-owner-context-r2/qcom_pmic_typec_5v.c',
 OEM+'pd5v-owner-context-r2/qcom_pmic_typec_5v.h',
 OEM+'pd5v-owner-context-r2/Makefile',
 OEM+'pd5v-owner-context-r2/delivery.json',
 OEM+'pd5v-owner-context-r2/build-result.json',
 OEM+'pd5v-owner-feasibility/board-opt-in-design.dtsi',
 OEM+'apsd-once-candidate/samurai-apsd-once.h',
 OEM+'apsd-phy-window-candidate/phy-qcom-snps-femto-v2.c',
 OEM+'apsd-phy-window-candidate/phy-qcom-snps-femto-v2-window.h',
 SESSION+'eud-runtime-window-candidate-r2/eud.c',
 SESSION+'eud-runtime-window-candidate/eud-com-window.h',
 OEM+'apsd-integration/current-r7/image-source-linkage.json',
 OEM+'apsd-tcpm-owner-candidate/board-linkage.json',
 OEM+'apsd-tcpm-owner-candidate/interface-contract.json',
 OEM+'apsd-lifecycle/oem/drivers--power--supply--qcom--smb5-lib.c',
 OEM+'apsd-lifecycle/oem/drivers--usb--phy--phy-msm-snps-hs.c',
 'charging-management-20261023/usb500-r8-eud-off-result.json',
 'charging-management-20261023/icon-r8-eud-off-result.json',
]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
evidence={path:dict(sha256=sha(REF/path),bytes=(REF/path).stat().st_size) for path in files}
anchors={
 OEM+'apsd-input-backend-candidate/samurai-apsd-input.inc':
  {'read_sample':5,'rerun_once':59,'unique_masked_transfer':82,'start':93,'withdraw':117},
 SESSION+'apsd-session-owner-candidate/samurai-apsd-owner.c':
  {'protocol_history':49,'entry_gate':92,'restore':103,'enter_windows':146,'read':168,'work':192,'notify':242,'join':254,'bus_register':276,'bus_unregister':313},
 OEM+'pd5v-owner-context-r2/qcom_pmic_typec_5v.c':
  {'status_regs':18,'control_regs':24,'policy':80,'off':89,'disable_off':115,'verify':198,'validate':272,'release':327,'bound_acquire':354,'quiesce':374,'complete':408,'create':422,'destroy':464},
 OEM+'apsd-phy-window-candidate/phy-qcom-snps-femto-v2.c':
  {'begin':239,'end':308,'runtime_suspend':387,'runtime_resume':401,'probe':759,'driver_without_remove_or_shutdown':840},
 SESSION+'eud-runtime-window-candidate-r2/eud.c':{'quiet_begin':1329,'no_bound_COM_ENODEV':1340},
 OEM+'apsd-lifecycle/oem/drivers--power--supply--qcom--smb5-lib.c':
  {'request_dpdm':1033,'rerun_apsd':1076,'pd_active':4319,'plugin':5080,'detach_once_reset':5158,'source_change_irq':5458,'vendor_once_rerun':5512},
 OEM+'apsd-lifecycle/oem/drivers--usb--phy--phy-msm-snps-hs.c':{'dpdm_enable':633,'dpdm_disable':672},
}
out=dict(schema='samurai-apsd-eud-off-next-block-source-evidence-v1',files=evidence,line_anchors=anchors,
 note='Anchors refer to exact cached bytes, not a live tree. Historical build/test receipts are not rerun.',
 source_tree_accessed=False,device_accessed=False,tests_rerun=False,build_invoked=False,SDK_invoked=False,Git_invoked=False)
(HERE/'source-evidence.json').write_text(json.dumps(out,indent=2)+'\n')
result=dict(schema='samurai-apsd-eud-off-next-block-design-v1',implemented=False,
 next_block='real PD5V R2 client bridge with pre-attach WAIT_FIRST_OFF and real owner lifetime/cancel/join',
 current_owner_gate_unchanged=True,APSD_transfer_enabled=False,Image501_payload_modified=False,
 sequence=['WAIT_BINDING','WAIT_FIRST_OFF','PD_DISABLED_WAIT_ATTACH','NEW_SINK_EPOCH','EXACT_SDP_CDP_READY'],
 remaining_before_command=['trusted revocable EUD-boot-off route capability, not absent-COM success',
  'PHY provider pre-devres withdrawal/cancel/join',
  'bound attempt identity, fresh physical read and final lease/cancel validation at one transfer boundary'],
 actual_EUD_off_topology='cached real direct-root NCM + native500 acceptance; no PD/route lease inferred',
 full_PD_supported=False,full_charging_adaptation_complete=False,
 source_evidence_sha256=sha(HERE/'source-evidence.json'),README_sha256=sha(HERE/'README.md'),
 device_accessed=False,tests_rerun=False,build_invoked=False,SDK_invoked=False,Git_invoked=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
delivery=dict(schema='samurai-apsd-eud-off-next-block-delivery-v1',files={n:sha(HERE/n) for n in ['README.md','source-evidence.json','result.json','freeze-evidence.py']})
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(result_sha256=sha(HERE/'result.json'),delivery_sha256=sha(HERE/'delivery.json'),input_files=len(files),implemented=False)))
