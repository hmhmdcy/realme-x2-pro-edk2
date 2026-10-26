"""Restore pinned original functions and local comparison snapshots; no device."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
REPO='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git'
COMMIT='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
FILES=['drivers/power/supply/qcom/smb5-lib.c','drivers/power/supply/qcom/smb5-lib.h',
       'drivers/power/supply/qcom/smb5-reg.h','drivers/power/supply/qcom/qpnp-smb5.c',
       'drivers/usb/phy/phy-msm-snps-hs.c','drivers/usb/dwc3/dwc3-msm.c','Makefile',
       'arch/arm64/boot/dts/19781/sm8150-usb.dtsi','arch/arm64/boot/dts/19781/sm8150-pmic-overlay.dtsi',
       'arch/arm64/boot/dts/19781/sm8150-mtp.dtsi','arch/arm64/boot/dts/19781/pm8150b.dtsi']
TARGETS={
 'drivers/power/supply/qcom/smb5-lib.c':['smblib_apsd_enable','smblib_request_dpdm','smblib_rerun_apsd',
  'smblib_rerun_apsd_if_required','smblib_usb_plugin_locked','usb_plugin_irq_handler',
  'usb_source_change_irq_handler','typec_src_insertion','typec_src_removal','typec_attach_detach_irq_handler',
  'smblib_set_prop_pd_active','smblib_pr_swap_detach_work','oppo_chargerid_switch_work','typec_disable_cmd_work'],
 'drivers/power/supply/qcom/qpnp-smb5.c':['smb5_configure_typec','smb5_determine_initial_status','smb5_request_interrupt',
  'smbchg_set_chargerid_switch_val'],
 'drivers/usb/phy/phy-msm-snps-hs.c':['msm_hsphy_dpdm_regulator_enable','msm_hsphy_dpdm_regulator_disable',
  'msm_hsphy_dpdm_regulator_is_enabled','msm_hsphy_regulator_init','msm_hsphy_init','msm_hsphy_set_suspend'],
 'drivers/usb/dwc3/dwc3-msm.c':['dwc_dpdm_cb']}


def extract(source,name):
    match=re.search(r'^(?:static\s+)?[\w\s*]+?\b'+name+r'\([^;]*?\)\n\{',source,re.M)
    if not match: raise ValueError(name)
    start=match.start()
    while source[start]=='\n':start+=1
    end=source.index('\n}',match.end())+2
    body=source[start:end]
    return body,source.count('\n',0,start)+1


def main():
    (HERE/'oem').mkdir(exist_ok=True);(HERE/'current').mkdir(exist_ok=True)
    records=[];functions=[];sources={};bodies={}
    for name in FILES:
        raw=subprocess.check_output(['git','--git-dir='+REPO,'show',COMMIT+':'+name])
        if name.endswith('smb5-lib.c'):assert sha(raw)=='5203488026f12fddc65ca899f16c8eb461e0da08dc151c4c5be18501204342a8'
        (HERE/'oem'/name.replace('/','--')).write_bytes(raw);sources[name]=raw.decode()
        records.append(dict(path=name,bytes=len(raw),sha256=sha(raw),url=
            'https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/'+COMMIT+'/'+name))
    for path,names in TARGETS.items():
        for name in names:
            body,line=extract(sources[path],name);bodies[name]=body
            functions.append(dict(function=name,path=path,line=line,end_line=line+body.count('\n'),sha256=sha(body.encode())))
    (HERE/'oem-functions.inc').write_text('\n\n'.join('/* '+r['path']+':'+str(r['line'])+' */\n'+bodies[r['function']] for r in functions)+'\n')
    for label,names in [('smb',['smblib_apsd_enable','smblib_request_dpdm','smblib_rerun_apsd',
         'smblib_rerun_apsd_if_required','usb_source_change_irq_handler']),
        ('phy',['msm_hsphy_dpdm_regulator_enable','msm_hsphy_dpdm_regulator_disable','msm_hsphy_dpdm_regulator_is_enabled'])]:
        (HERE/('tested-oem-'+label+'.inc')).write_text('\n\n'.join(bodies[n] for n in names)+'\n')
    macro_names=['USBIN_BASE','TYPEC_BASE','APSD_STATUS_REG','APSD_DTC_STATUS_DONE_BIT',
        'APSD_RESULT_STATUS_REG','SDP_CHARGER_BIT','CDP_CHARGER_BIT','DCP_CHARGER_BIT','FLOAT_CHARGER_BIT',
        'QC_CHARGER_BIT','QC_AUTH_DONE_STATUS_BIT','ENUMERATION_DONE_BIT','SLOW_PLUGIN_TIMEOUT_BIT',
        'HVDCP_CHECK_TIMEOUT_BIT','CMD_APSD_REG','APSD_RERUN_BIT','USBIN_OPTIONS_1_CFG_REG',
        'BC1P2_SRC_DETECT_BIT','TYPE_C_CFG_REG','BC1P2_START_ON_CC_BIT','LEGACY_CABLE_STATUS_REG',
        'TYPEC_LEGACY_CABLE_STATUS_BIT','TYPEC_NONCOMP_LEGACY_CABLE_STATUS_BIT',
        'USB2_PHY_USB_PHY_HS_PHY_CTRL2','USB2_SUSPEND_N_SEL','USB2_SUSPEND_N',
        'USB2_PHY_USB_PHY_UTMI_CTRL0','OPMODE_MASK','OPMODE_NONDRIVING',
        'USB2_PHY_USB_PHY_CFG0','UTMI_PHY_DATAPATH_CTRL_OVERRIDE_EN']
    macros=[];definitions=[]
    for name in macro_names:
        path=('drivers/usb/phy/phy-msm-snps-hs.c' if name.startswith(('USB2_','UTMI_','OPMODE_'))
              else 'drivers/power/supply/qcom/smb5-reg.h')
        match=re.search(r'^#define\s+'+name+r'\s+[^\n]+',sources[path],re.M);assert match,name
        definitions.append(match[0]);macros.append(dict(name=name,path=path,
            line=sources[path].count('\n',0,match.start())+1,definition=match[0]))
    (HERE/'oem-registers.inc').write_text('\n'.join(definitions)+'\n')
    comparison=[]
    # The shared source354 mount disappeared during this read-only audit.
    # Do not remount or claim these older cached files are authoritative R7 bytes.
    for name,path in [('cached-femto-v2.c',Path('/mnt/e/edk2-samurai-out/rx38-sources/phy-qcom-snps-femto-v2.c')),
                      ('cached-qcom-smbx.c',Path('/mnt/e/edk2-samurai-out/kernel76/charging-research/mainline--drivers--power--supply--qcom_smbx.c'))]:
        raw=path.read_bytes();(HERE/'current'/name).write_bytes(raw)
        comparison.append(dict(path=str(path),bytes=len(raw),sha256=sha(raw),
                               scope='historical cache; not an authoritative current R7 source snapshot'))
    for name in ['samurai-usb-input.c','samurai-usb-input-decode.h']:
        path=HERE.parents[1]/'charging-management-20261023'/name
        raw=path.read_bytes();(HERE/'current'/name).write_bytes(raw)
        comparison.append(dict(path=str(path),bytes=len(raw),sha256=sha(raw)))
    manifest=dict(commit=COMMIT,origin=subprocess.check_output(['git','--git-dir='+REPO,'remote','get-url','origin']).decode().strip(),
        files=records,functions=functions,registers=macros,current_comparison=comparison,phone_accessed=False,sdk_accessed=False,
        shared_source_modified=False,hardware_writes_performed=False)
    (HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'restored_complete_functions':len(functions),'oem_files':len(records),'current_files':len(comparison)}))


if __name__=='__main__':main()
