"""Bound the exact init write using local pinned primary-source bytes only."""
from pathlib import Path
import hashlib
import html
import json
import re

HERE=Path(__file__).resolve().parent
LIFE=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((LIFE/'source-manifest.json').read_text())
paths={'qpnp':'drivers/power/supply/qcom/qpnp-smb5.c',
       'lib':'drivers/power/supply/qcom/smb5-lib.c',
       'reg':'drivers/power/supply/qcom/smb5-reg.h'}
texts={};source_rows=[]
for key,path in paths.items():
    p=LIFE/'oem'/path.replace('/','--')
    row=next(r for r in manifest['files'] if r['path']==path)
    assert sha(p)==row['sha256']
    texts[key]=p.read_text();source_rows.append(row)

def function(key,name):
    text=texts[key]
    m=re.search(r'^(?:static\s+)?[\w\s*]+?\b'+name+r'\([^;]*?\)\n\{',text,re.M)
    assert m,name
    start=m.start()
    while text[start]=='\n':start+=1
    end=text.index('\n}',m.end())+2
    body=text[start:end]
    return body,dict(function=name,path=paths[key],line=text[:start].count('\n')+1,
                     end_line=text[:end].count('\n')+1,sha256=hashlib.sha256(body.encode()).hexdigest())

targets={'qpnp':['smb5_probe','smb5_init_hw','smb5_configure_typec','smb5_determine_initial_status'],
    'lib':['smblib_masked_write','smblib_init','usb_plugin_irq_handler','smblib_usb_plugin_locked','typec_disable_cmd_work']}
bodies={};rows=[]
for key,names in targets.items():
    for name in names:
        body,row=function(key,name);bodies[name]=body;rows.append(row)
(HERE/'oem-scope-functions.inc').write_text('\n\n'.join(bodies.values())+'\n')
probe=bodies['smb5_probe'];init=bodies['smb5_init_hw'];configure=bodies['smb5_configure_typec']
assert probe.index('smb5_init_hw(chip)')<probe.index('smb5_determine_initial_status(chip)')
assert 'smb5_configure_typec(chg)' in init
assert configure.index('smblib_apsd_enable(chg, true)')<configure.index('BC1P2_START_ON_CC_BIT, 0')
assert configure.index('smblib_hvdcp_detect_enable(chg, false)')<configure.index('BC1P2_START_ON_CC_BIT, 0')
assert 'smblib_request_dpdm' not in configure
assert 'smblib_request_dpdm' not in bodies['smblib_init']
assert 'regmap_update_bits(chg->regmap, addr, mask, val)' in bodies['smblib_masked_write']
assert 'usb_plugin_irq_handler(0, &irq_data)' in bodies['smb5_determine_initial_status']
assert 'smblib_usb_plugin_locked(chg)' in bodies['usb_plugin_irq_handler']
assert 'smblib_request_dpdm(chg, true)' in bodies['smblib_usb_plugin_locked']
# The only init-hw rerun site is the explicit PMI632-only block, not PM8150B.
assert re.search(r'if \(chg->smb_version == PMI632_SUBTYPE\) \{\n\s*schgm_flash_init\(chg\);\n\s*smblib_rerun_apsd_if_required\(chg\);\n\s*\}',init)

v4_path=LIFE/'smb5-v4-20260820.html'
assert sha(v4_path)=='695d810663f59a1ffe31ed86ac78e07b3a9b013f890f8243c684300d9a1da6e4'
v4=html.unescape(v4_path.read_text())
seq=v4[v4.index('+static const struct smb_init_register smb5_init_seq[]'):]
assert seq.index('.addr = USBIN_TYPE_C_CFG')<seq.index('.addr = USBIN_OPTIONS_1_CFG')
assert re.search(r'\.addr = USBIN_TYPE_C_CFG,\n\+\s*\.mask = APSD_START_ON_CC_BIT,\n\+\s*\.val = 0',seq)
v4_probe=v4[v4.index(' static int smb_probe(struct platform_device *pdev)'):]
assert v4_probe.index('USBIN_SUSPEND_BIT, USBIN_SUSPEND_BIT')<v4_probe.index('CHARGING_ENABLE_CMD_BIT, 0')<v4_probe.index('rc = smb_init_hw(chip, match_data->init_seq')
assert 'dpdm' not in v4.lower()
excerpts=[]
lines=v4.splitlines()
for start,end in [(120,139),(889,907),(1044,1065),(1113,1192)]:
    excerpts.append('HTML cache lines %d..%d\n%s'%(start,end,'\n'.join(lines[start-1:end])))
(HERE/'v4-scope-excerpts.txt').write_text('\n\n'.join(excerpts)+'\n')
result=dict(passed=True,scope='source-effect and probe-order evidence, not online write validation',
    oem_commit=manifest['commit'],oem_sources=source_rows,actual_functions=rows,
    v4=dict(url='https://lists.openwall.net/linux-kernel/2026/08/20/748',
        message_id='20260820-submit-qcom-smbx-send-v1-v4-2-818dabb2771e@snyders.xyz',
        base_commit='99b38cda3f4c486cfbc40f3c8ede1703594e9f13',html_sha256=sha(v4_path)),
    exact_operation=dict(address='0x1358',mask='0x80',value='0x00',mechanism='regmap_update_bits',
        writes_applies_to='USBIN BC1.2 start-on-CC configuration',example_old='0xc0',example_new='0x40',other_bits_preserved=True),
    conclusions=dict(standalone_init_write_supported_by_source=True,
        full_dwc_eud_phy_tokens_required_by_source_for_this_bit=False,
        explicit_cmd_apsd_write_in_exact_operation=False,role_or_pd_write_in_exact_operation=False,
        phy_or_dpdm_operation_in_exact_operation=False,budget_or_charger_limit_write_in_exact_operation=False,
        oem_enable_detection_precedes_clear=True,oem_explicit_initial_plugin_dpdm_follows_init_clear=True,
        upstream_clear_precedes_detection_enable=True,upstream_probe_suspends_input_before_init=True,
        online_clear_has_no_indirect_auto_trigger_proven=False,online_clear_safe_proven=False,
        sdp_to_cdp_change_guaranteed=False,bootloader_analog_or_pd_state_inactive_proven=False),
    old_suites_repeated=False,phone_accessed=False,ssh_executed=False,sdk_invoked=False,hardware_writes=0,
    files={n:sha(HERE/n) for n in ['audit-scope.py','oem-scope-functions.inc','v4-scope-excerpts.txt']})
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
