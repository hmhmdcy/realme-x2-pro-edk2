"""Finalize only the existing new host-side cohort; no packaging/device replay."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
OUT=Path('E:/edk2-samurai-out/charging-management-20261023/native-usb-pm-budget504-cohort-private-01')
sha=lambda b:hashlib.sha256(b).hexdigest()
def encode(d):return (json.dumps(d,indent=2)+'\n').encode()
def main():
    assert not (HERE/'delivery.json').exists()
    result=json.loads((OUT/'result.json').read_bytes());assert result['passed'] and not result['installed'] and result['rootfs_member_count']==2
    assert result['source_sha256']==sha((HERE/'cohort.py').read_bytes())=='911d1ebd06fcf852ff0f8bddcb1c8d2caf69dbe38eeeebbf71c83b506abbd8e3'
    for name,row in result['files'].items():
        raw=(OUT/name).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    for name in ['manifest.json','cohort.json']:
        target=HERE/name;assert not target.exists();target.write_bytes((OUT/name).read_bytes())
    (HERE/'payload-result.json').write_bytes((OUT/'result.json').read_bytes())
    execution=dict(passed=True,host_commands=[
        dict(argv=['python','-B','cohort.py'],returncode=0,tool_chunk='3fd7d3',output_absent_at_check=True),
        dict(argv=['python','-B','cohort.py','build','--execute'],returncode=0,tool_chunk='addbcf',single_materialization=True),
        dict(argv=['python','-B','cohort.py','audit'],returncode=0,tool_chunk='965081',readonly_existing_artifacts=True)],
        private_result_sha256=sha((OUT/'result.json').read_bytes()),
        device_SDK_storage_Git_used=False,installed=False)
    (HERE/'execution-receipt.json').write_bytes(encode(execution))
    names=['cohort.py','prepare-inputs.py','input-pins.json','test-cohort.py','test-result.json',
        'prepare-carrier.py','carrier-input.json','test-carrier-binding.py','package-verification.json',
        'carrier-binding-delta.patch','README.md','manifest.json','cohort.json','payload-result.json','execution-receipt.json','freeze.py']
    delivery=dict(passed=True,schema='samurai-native-usb-pm-budget504-offline-cohort-v1',
        files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in names},
        private_outputs=result['files'],rootfs_member_count=2,
        reused_package_cases=10,new_binding_cases=4,
        Image504_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4',
        logdump_sha256='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83',
        USB_module_sha256='2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448',
        only_USB_and_manifest_replaced=True,original_policy_and_protection_retained=True,
        installed=False,new_guard_or_deployment_binding=False,device_SDK_storage_Git_used=False,
        hardware_PM_or_icon_accepted=False)
    (HERE/'delivery.json').write_bytes(encode(delivery))
    print(json.dumps(dict(passed=True,files=len(names),delivery_sha256=sha((HERE/'delivery.json').read_bytes()))))
if __name__=='__main__':main()
