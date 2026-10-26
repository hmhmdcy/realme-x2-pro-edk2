"""Wire real ADC5 VBUS and the TCPM allowance consumer; never access a phone."""
from pathlib import Path
import hashlib,json,shutil,struct,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'tcpm-measured-vbus-board-private-01'
ADC='/soc@0/spmi@c440000/pmic@2/adc@3100'
TC='/soc@0/spmi@c440000/pmic@2/typec@1500'
CHARGER='/soc@0/geniqup@8c0000/i2c@884000/charger@5c'
sha=lambda b:hashlib.sha256(b).hexdigest()
cells=lambda *v:struct.pack('>'+'I'*len(v),*v)

def main():
    old_result=REF/'charging-oem-audit-20261023/tcpm-usb-budget-candidate/dtb-result.json'
    assert sha(old_result.read_bytes())=='85edb8eb940137203e86f70057222cb563953601c02b75a04ef30b29755f1763'
    old=json.loads(old_result.read_bytes());assert old['passed']
    path=Path(old['DTB_path']);before=path.read_bytes();assert sha(before)==old['DTB_sha256']
    source=(REF/'kernel104/verify-firmware.py').read_text()
    assert sha(source.encode())=='2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
    scope={};exec(compile(source.split('\ndt_audit=',1)[0],'verified-FDT-parser','exec'),scope)
    parse=scope['fdt_nodes'];nodes=parse(before)
    assert nodes[ADC]['compatible']==b'qcom,spmi-adc5\0'
    assert nodes[CHARGER]['compatible']==b'mps,mp2650\0'
    assert nodes[TC]['compatible']==b'qcom,pm8150b-typec\0'
    assert ADC+'/channel@8' not in nodes and 'io-channels' not in nodes[TC]
    assert 'io-channel-names' not in nodes[TC] and 'typec-supply' not in nodes[CHARGER]
    assert nodes[ADC]['phandle']==cells(0x11b) and nodes[TC]['phandle']==cells(0x15b)
    assert not OUT.exists(),'Inspect prior result, never overwrite derived evidence'
    OUT.mkdir(mode=0o700);target=OUT/'samurai-tcpm-measured-vbus-private.dtb';shutil.copyfile(path,target)
    subprocess.run(['fdtput','-c',str(target),ADC+'/channel@8'],check=True)
    for node,prop,kind,values in [
        (ADC+'/channel@8','reg','x',['8']),
        (ADC+'/channel@8','qcom,pre-scaling','x',['1','10']),
        (ADC+'/channel@8','label','s',['usb_in_v_div_16']),
        (TC,'io-channels','x',['11b','8']),
        (TC,'io-channel-names','s',['vbus']),
        (CHARGER,'typec-supply','x',['15b']),
    ]:subprocess.run(['fdtput','-t',kind,str(target),node,prop,*values],check=True)
    expected={k:dict(v) for k,v in nodes.items()}
    expected[ADC+'/channel@8']={'reg':cells(8),'qcom,pre-scaling':cells(1,16),'label':b'usb_in_v_div_16\0'}
    expected[TC].update({'io-channels':cells(0x11b,8),'io-channel-names':b'vbus\0'})
    expected[CHARGER]['typec-supply']=cells(0x15b)
    assert parse(target.read_bytes())==expected
    assert sha(path.read_bytes())==old['DTB_sha256']
    result=dict(passed=True,phone_accessed=False,installed=False,source_result_sha256=sha(old_result.read_bytes()),
        base_DTB_sha256=old['DTB_sha256'],DTB_path=str(target),DTB_sha256=sha(target.read_bytes()),DTB_bytes=target.stat().st_size,
        added_ADC_channel=8,ADC_prescale=[1,16],ADC_phandle=0x11b,typec_phandle=0x15b,
        changed_existing_properties=[TC+':io-channels',TC+':io-channel-names',CHARGER+':typec-supply'],
        all_other_nodes_and_properties_exact=True,PDO_and_voltage_requests_unchanged=True,
        inherited_APSD_trial_configuration_unchanged=True,ADC_physical_voltage_validated=False,
        requires_consumer_and_protocol_control_integration=True,new_boot_or_Image=False)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/'dtb-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

if __name__=='__main__':main()
