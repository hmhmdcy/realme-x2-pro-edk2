from pathlib import Path
from hashlib import sha256
import json, subprocess

src=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel67')
repo=Path('/home/cy122/edk2-samurai/repo')
names=('arch/arm64/boot/dts/qcom/sm8150.dtsi','drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c','drivers/phy/qualcomm/Kconfig','drivers/phy/qualcomm/Makefile','Documentation/devicetree/bindings/phy/qcom,usb-snps-femto-v2.yaml')
files={name:sha256((src/name).read_bytes()).hexdigest() for name in names}
initramfs=Path('/home/cy122/x2pro-linux/initramfs')
modules=list(initramfs.rglob('*.ko'))
assert not modules
assert '"qcom,sm8150-usb-hs-phy"' in (src/names[1]).read_text()
assert 'CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y\n' in (src/'.config').read_text()
assert 'kernel/drivers/phy/qualcomm/phy-qcom-snps-femto-v2.ko\n' in (src/'modules.builtin').read_text()
loader=repo/'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
text=loader.read_text()
begin=text.index('// SAMURAI: where the mainline Linux kernel lives')
end=text.index('STATIC\nVOID\nSamuraiRegisterKernelBootOption',begin)
(out/'boot-loader-excerpt.c').write_text(text[begin:end])
result=dict(primary_hs_phy_address='0x088e2000',compatible='qcom,sm8150-usb-hs-phy',config='PHY_QCOM_USB_SNPS_FEMTO_V2',before='m',after='y',only_config_change=True,initramfs_kernel_modules=len(modules),built_in_manifest_entry=True,source_hashes=files,loader_path=str(loader.relative_to(repo)),loader_sha256=sha256(loader.read_bytes()).hexdigest(),edk2_base=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),firmware_dtb_supplied_by='DtPlatformDxe EFI configuration table',fat_dtb_override_in_current_load_options=False,usb_runtime_result='must use independently verified runtime exports',primary_urls=['https://raw.githubusercontent.com/torvalds/linux/master/drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c','https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/phy/qcom,usb-snps-femto-v2.yaml'])
(out/'usb-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
