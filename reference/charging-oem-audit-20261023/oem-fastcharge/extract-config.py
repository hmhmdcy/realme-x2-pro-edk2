"""Recover only the fixed 19781 fast-charge source configuration, not live DT."""
from pathlib import Path
import hashlib,json,re,sys
sys.dont_write_bytecode=True
from fastcharge_codec import *
CACHE=Path('E:/edk2-samurai-out/kernel83') if sys.platform=='win32' else Path('/mnt/e/edk2-samurai-out/kernel83')
PREFIX='realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--'
def original(name):return CACHE/(PREFIX+name.replace('/','--'))
def block(text,name):
    start=uncomment(text).index(name)
    clean=uncomment(text);opening=clean.index('{',start);depth=1;i=opening+1
    while depth:
        depth+=(clean[i]=='{')-(clean[i]=='}');i+=1
    return clean[opening+1:i-1],text[:start].count('\n')+1
def properties(text):
    result={}
    for m in re.finditer(r'([a-zA-Z0-9_,.-]+)\s*(?:=\s*([^;]+))?;',text):
        key,value=m[1],m[2]
        if value is None:result[key]=True
        elif value.strip().startswith('<'):
            value=value.strip()[1:-1].split()
            result[key]=[int(x,0) if re.fullmatch(r'0[xX][0-9a-fA-F]+|[0-9]+',x) else x for x in value]
        else:result[key]=re.findall(r'"([^"]*)"',value)
    return result
overlay='arch/arm64/boot/dts/19781/sm8150-pmic-overlay.dtsi'
policy='arch/arm64/boot/dts/19781/pm8150b.dtsi'
text=original(overlay).read_text();fast,line=block(text,'stm8s_fastcg@26')
divider,divline=block(text,'da9313-divider@68')
props=properties(fast);dprops=properties(divider)
pprops=properties(uncomment(original(policy).read_text()))
selected={k:v for k,v in pprops.items() if k.startswith('qcom,ffc') or k.startswith('qcom,ff1') or k in ['qcom,vooc_project','qcom,vbatt_num','qcom,dual_ffc']}
pintext=cached('arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi').read_text()
pins={}
for name in ['charging_switch1_active','charging_switch1_sleep','charging_reset_active','charging_reset_sleep',
             'charging_clock_active','charging_clock_sleep','charging_data_active','charging_data_sleep']:
    body,pinline=block(pintext,name+':');pins[name]=dict(line=pinline,source=body.strip())
branches,_=firmware_branches(cached(HEADER).read_text())
images={str(flag):dict(config_OPLUS_SM8150R_CHARGER=flag,symbol=SYMBOL,source_line=b['line'],**inspect_stm8s(b['data'])) for flag,b in branches.items()}
inputs={overlay:dict(local=str(original(overlay)),sha256=sha(original(overlay).read_bytes())),
 policy:dict(local=str(original(policy)),sha256=sha(original(policy).read_bytes()))}
audit=CACHE/'androidr-source-audit.json';cfg=CACHE/'cyborgdc2000--kernel_realme_sm8150--arch--arm64--configs--samurai_defconfig'
assert 'CONFIG_OPLUS_SM8150R_CHARGER=y' in cfg.read_text()
r=dict(repository='realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source',commit='23172a1571bd91156032cc9fef16284a82b63d2c',
 inputs=inputs,fastcharge_node=dict(source=overlay,line=line,bus='qupv3_se15_i2c',properties=props),
 divider_node=dict(source=overlay,line=divline,bus='qupv3_se15_i2c',properties=dprops),
 source_board_selection='missing ASIC and MCU ID GPIO properties select STM8S in OEM fallback; no runtime IC identification performed',
 explicit_regulator_supply_in_node=False,regulator_rail='not identified by this node or stm8s probe; do not infer voltage/power ownership',
 ffc_properties=selected,pinctrl=pins,firmware_images=images,
 branch_evidence=dict(config='CONFIG_OPLUS_SM8150R_CHARGER=y',source=str(cfg),sha256=sha(cfg.read_bytes()),
  scope='cached third-party samurai build configuration and previous source audit; not an acquired official production .config or MCU version'),
 firmware_update_newmethod_present='qcom,vooc_fw_update_newmethod' in props,
 gpio_ID_properties_present=[x for x in ['qcom,vooc_asic_id-gpio','qcom,vooc_mcu_id-gpio'] if x in props],
 live_configuration_read=False,phone_accessed=False,ssh_executed=False,sdk_invoked=False)
(HERE/'config-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,node=props['compatible'],firmware_type=props['qcom,vooc-fw-type'],images=images),indent=2))
