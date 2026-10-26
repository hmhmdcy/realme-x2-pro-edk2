"""Freeze only local E/private source and receipts. No storage/device access."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda name,obj:(HERE/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
t=json.loads((HERE/'test-result.json').read_text());assert t['passed'] and t['actual_function_count']==22 and t['group_count']==7
for n,h in t['tested_files'].items():assert sha(HERE/n)==h,n
old=HERE/'build-before-power-gate-result.json'
if not old.exists():old.write_bytes((HERE/'build-result.json').read_bytes())
previous=json.loads(old.read_text());assert previous['passed']
assert previous['source_files']['qcom_pmic_typec_5v.c']!=sha(HERE/'qcom_pmic_typec_5v.c')
dump('build-result.json',dict(passed=False,blocked=True,current_source_object_compiled=False,
 reason='Original /mnt/samurai-full282 mount absent: explicit preflight assertion stopped before original helper call, any mount, source copying or compiler invocation',
 attempted_targets=['drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_5v.o','drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.o'],
 source_files={n:sha(HERE/n) for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','qcom_pmic_typec.c','qcom_pmic_typec.h','Makefile']},
 test_receipt_sha256=sha(HERE/'test-result.json'),original_helper_called=False,remounted=False,anchor_created=False,
 source_shared_modified=False,SDK_invoked=False,Git_invoked=False,phone_accessed=False,
 previous_W1_receipt=dict(file=old.name,sha256=sha(old),valid_only_before_power_gate_fix=True),
 next_step='root may restore original storage with original guard/helper in its own window; only then rebuild these two private objects; no Image/module link'))
sources=[]
def source(name,path,lines):
 sources.append(dict(name=name,path=str(path),bytes=path.stat().st_size,sha256=sha(path),references=lines))
fixed=HERE.parent/'apsd-tcpm-owner-candidate/sources'
source('current_qcom_pdphy',fixed/'drivers--usb--typec--tcpm--qcom--qcom_pmic_typec_pdphy.c',[
 dict(function='qcom_pmic_typec_pdphy_reset_on',first_line=106,last_line=125,meaning='TX=0 then FILTER=0; void error logging'),
 dict(function='qcom_pmic_typec_pdphy_disable',first_line=484,last_line=494,meaning='EN=0 but void reset_on failure not propagated'),
 dict(function='pmic_typec_pdphy_reset',first_line=496,last_line=508,meaning='disable then re-enable, prohibited for disabled-only mode'),
 dict(function='qcom_pmic_typec_pdphy_start',first_line=510,last_line=536,meaning='enable supply/reset/PD IRQs'),
 dict(function='qcom_pmic_typec_pdphy_stop',first_line=538,last_line=551,meaning='IRQ disable/reset_work join/TX-filter zero/regulator reference drop, no EN/BIST clear')])
source('current_qcom_port',fixed/'drivers--usb--typec--tcpm--qcom--qcom_pmic_typec_port.c',[
 dict(first_line=47,last_line=59,meaning='SM_STATUS VSAFE5V bit5, VSAFE0V bit6; MISC source/VBUS/CC facts'),
 dict(function='qcom_pmic_typec_port_vbus_toggle',first_line=293,last_line=325,meaning='actual SM vSafe status poll; not ACOK inference'),
 dict(function='qcom_pmic_typec_port_start',first_line=636,last_line=695,meaning='normal port_start writes TRY_SNK and configures/enables interrupts')])
source('current_qcom_parent',fixed/'drivers--usb--typec--tcpm--qcom--qcom_pmic_typec.c',[
 dict(function='qcom_pmic_typec_probe',first_line=31,last_line=125,meaning='normal real platform binding/start order; special branch placed before port_probe')])
source('current_tcpm',fixed/'drivers--usb--typec--tcpm--tcpm.c',[
 dict(function='tcpm_reset_port',first_line=5146,last_line=5190,meaning='reset local attached/pd_capable and disable receive on physical detach path'),
 dict(function='tcpm_detach',first_line=5192,last_line=5207,meaning='clear BIST then reset_port'),
 dict(first_line=5778,last_line=5797,meaning='new SNK_STARTUP initializes message IDs and explicit_contract=false; a firmware inherited active connection is not this transition')])
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pd5v-oem-private')
oem=private/'androidr--qpnp-pdphy.c'
assert sha(oem)=='aee34f0586df32e0229bb83890bea399b635c73f8f7c5e9a9ecae67b201e0eeb'
source('OEM_AndroidR_pdphy',oem,[
 dict(function='pd_phy_open',first_line=358,last_line=422,meaning='GoodCRC roles, EN cycle, filter, opened and IRQ activation'),
 dict(function='pd_phy_close',first_line=575,last_line=610,meaning='opened false/IRQ off, BIST0, TX0, EN0, power-ref drop; void and incomplete errno/readback'),
 dict(function='pd_phy_bist_mode',first_line=694,last_line=706,meaning='independent BIST transmit/test producer requires explicit clear')])
source('OEM_19781_DTS',HERE.parent/'apsd-lifecycle/oem/arch--arm64--boot--dts--19781--pm8150b.dtsi',[
 dict(first_line=608,last_line=638,meaning='PD PHY 1700/L2 supply/IRQ/default sink cap declaration; not actual active contract')])
source('OEM_SMB5_registers',HERE.parent/'apsd-lifecycle/oem/drivers--power--supply--qcom--smb5-reg.h',[
 dict(first_line=307,last_line=311,meaning='1362 HVDCP AUTH/AUTO/ENABLE and BC source detection bit definitions'),
 dict(first_line=419,last_line=427,meaning='1544 role/TRY/sink-only bits')])
source('actual_cached_R8_controls',REF/'charging-management-20261023/pd-controls-r8-result.json',[
 dict(meaning='two real historical snapshots: 1544=2,1362=18,PD TX/EN/filter/BIST0; explicitly not PD-inactive proof, no off-vSafe0V capture')])
dump('evidence.json',dict(sources=sources,official_androidr=json.loads((HERE/'androidr-source-result.json').read_text()),
 same_phy_bytes_in_old_official_source=sha(private/'drivers--usb--pd--qpnp-pdphy.c')==sha(oem),
 fixed_Image363_linkage=dict(file='../apsd-integration/current-r7/image-source-linkage.json',sha256=sha(HERE.parent/'apsd-integration/current-r7/image-source-linkage.json'),scope='three qcom original ba61 source files; current TCPM snapshot not falsely claimed byte-identical to original ba61'),
 board_receipt_sha256=sha(HERE/'board-result.json'),
 PD_inactive_current_hardware_proven=False,physical_off_vSafe0V_current_hardware_proven=False,
 new_device_or_storage_read=False))
c=(HERE/'qcom_pmic_typec_5v.c').read_text()
assert 'EXPORT_SYMBOL' not in c and '0x1341' not in c and 'CMD_APSD' not in c
dump('result.json',dict(frozen=True,candidate_implemented=True,default_enabled=False,automatic_consumer=False,
 control_source_sha256=sha(HERE/'qcom_pmic_typec_5v.c'),patch_sha256=sha(HERE/'pd5v-owner.patch'),
 contract_sha256=sha(HERE/'contract.json'),test_passed=True,actual_functions=22,test_groups=7,test_receipt_sha256=sha(HERE/'test-result.json'),
 final_object_build_passed=False,final_object_build_blocked_original_mount_absent=True,build_receipt_sha256=sha(HERE/'build-result.json'),
 pre_power_fix_object_success_only=True,source_evidence_sha256=sha(HERE/'evidence.json'),
 unresolved_safety_bug_known=False,unresolved_before_use=['final two-object rebuild after original volume safely restored','independent code/lifecycle review','no physical off-vSafe0V/control/next-attach/PM proof','no complete APSD route/source/epoch integration','no measured 5V or VOOC MCU exclusion'],
 runtime_PM_enabled=False,Image_or_module_linked=False,DTB_created=False,installed=False,
 phone_accessed=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False,shared_source_or_config_modified=False))
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'}
dump('delivery.json',dict(schema='samurai-pd-disabled-owner-delivery-v1',frozen=True,files=files,
 execution_allowed=False,current_compile_proven=False,reason='offline code/tests complete, final compile blocked rather than bypass original storage guard'))
print(json.dumps(dict(source=sha(HERE/'qcom_pmic_typec_5v.c'),patch=sha(HERE/'pd5v-owner.patch'),test=sha(HERE/'test-result.json'),build=sha(HERE/'build-result.json'),result=sha(HERE/'result.json'),delivery=sha(HERE/'delivery.json')),indent=2))
