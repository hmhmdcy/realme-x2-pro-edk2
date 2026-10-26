"""Write only this new offline leaf's fixed input pins; no device/build actions."""
from pathlib import Path
import copy,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parent.parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/input-pins.json'
assert sha(source.read_bytes())=='d0461dae337f9fe537751fd5222adde67b4071b340e8f1b23442071697a66935'
old=json.loads(source.read_bytes())
def pin(path,expected=None):
    p=Path(path);raw=p.read_bytes();digest=sha(raw)
    if expected:assert digest==expected,(str(p),digest)
    return dict(path=str(p),sha256=digest,bytes=len(raw))
receipts={
 'USB_delivery':('charging-oem-audit-20261023/usb-input-native-pm-link-candidate/delivery.json','2e94d81cd4100df7259e100740f1eecfb93ed9db29fddd07a2f0891524f3bca0'),
 'USB_link':('charging-oem-audit-20261023/usb-input-native-pm-link-candidate/ko-result.json','f56dd0ed9f082ef2509c5a2daa62fa4f7542dc8af99d6ffe62f483e87d305e95'),
 'Image504_delivery':('charging-oem-audit-20261023/dwc-image504-budget-fence-candidate/delivery.json','88aa96af5b451c7778503f89b549f8d7abd131bd8cf330c87368e7552147b482'),
 'Image504_build':('charging-oem-audit-20261023/dwc-image504-budget-fence-candidate/build-result.json','091d736b939438a509dc9ef34712b87afad50cd8c27f08ca19b571f3a1ab1ed9'),
 'Image504_root':('charging-management-20261023/image504-offline-root-review.json','c82519440baf15e6ab27f858d9d1fbb2a2d526efe57fda87d7654e870368f681')}
data=dict(schema='native-usb-pm-budget504-offline-inputs-v1',base_manifest=old['base_manifest'],old_USB=old['old_USB'],
    new_USB=pin('E:/edk2-samurai-out/charging-management-20261023/usb-input-native-pm-link-private-01/samurai-usb-input-pm-link-private.ko','2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448'),
    old_protection_archive=old['old_protection_archive'],retained=old['retained'],
    carriers=dict(boot=pin('E:/edk2-samurai-out/charging-management-20261023/gauge-image501-boot-private-01/boot-gauge501-private.img','97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'),
        native_DTB=pin('E:/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb','9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'),
        rollback_logdump=old['carriers']['logdump']),
    receipts={name:pin(REF/path,expected) for name,(path,expected) in receipts.items()},
    original_method=pin(REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/cohort.py','421edb515a280fc575e3c37b6b5da1643179ac30b739469b57d8ad9fe8c4e7c7'))
target=HERE/'input-pins.json';assert not target.exists()
target.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(dict(passed=True,only_pins_written=True,input_pins_sha256=sha(target.read_bytes()))))
