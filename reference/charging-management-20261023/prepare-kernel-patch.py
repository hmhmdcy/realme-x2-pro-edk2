"""Export maintained kernel integration without changing the shared checkout."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

ref=Path(__file__).resolve().parent
sys.path.insert(0,str(ref.parent/'kernel284'));import storage
source=storage.mounted_build().parent/'source354'
files=['samurai-mp2650.c','mp2650-core.h','charge-cycle.h','charging-notify.h','oem-profile.h','gauge-protocol.h',
       'gauge-i2c.h','samurai-usb-input.c','samurai-usb-input-decode.h','samurai-gauge-protection.c']
changes={}
directory='drivers/power/supply/'
for name in files:
    assert not (source/directory/name).exists()
    changes[directory+name]=('',(ref/name).read_text())
name=directory+'Makefile';before=(source/name).read_text()
changes[name]=(before,before+'''\n# RMX1931 ordinary charging management
obj-$(CONFIG_CHARGER_SAMURAI_MP2650) += samurai-mp2650.o
obj-$(CONFIG_SAMURAI_USB_INPUT) += samurai-usb-input.o
obj-$(CONFIG_BATTERY_SAMURAI_GAUGE_PROTECTION) += samurai-gauge-protection.o
''')
name=directory+'Kconfig';before=(source/name).read_text()
changes[name]=(before,before+'''
config CHARGER_SAMURAI_MP2650
	tristate "Realme X2 Pro ordinary charging manager"
	depends on I2C && OF && POWER_SUPPLY && ARCH_QCOM
	help
	  OEM-profile MP2650 policy with fresh two-cell and protection data.
	  Starts inhibited. The board service explicitly selects runtime wiring
	  and requests managed ordinary charging after suppliers are available.

config SAMURAI_USB_INPUT
	tristate "Realme X2 Pro PM8150B input allowance"
	depends on REGMAP && OF && POWER_SUPPLY && ARCH_QCOM
	help
	  Read-only source detection and native DWC3 accepted current allowance.

config BATTERY_SAMURAI_GAUGE_PROTECTION
	tristate "Realme X2 Pro factory gauge protection observation"
	depends on I2C && OF && POWER_SUPPLY && ARCH_QCOM
	help
	  Fresh read-only status from the installed factory-family 2719 gauge.
	  Does not program protection FETs, unseal, OTP or data flash.
''')
name='arch/arm64/boot/dts/qcom/sm8150-samurai.dts';before=(source/name).read_text()
assert 'usb-psy-name' not in before
assert 'usb_1_dwc3:' in (source/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text()
changes[name]=(before,before+'''\n/* Native configuration/reset/suspend USB allowance for the board supply. */
&usb_1_dwc3 {
	usb-psy-name = "samurai-usb-input";
};
''')
patch=''
for name,(old,new) in changes.items():
    patch+='diff --git a/'+name+' b/'+name+'\n'
    if not old:patch+='new file mode 100644\n'
    patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
        fromfile='a/'+name if old else '/dev/null',tofile='b/'+name))
target=ref/'kernel-integration.patch';target.write_text(patch)
config='CONFIG_CHARGER_SAMURAI_MP2650=m\nCONFIG_SAMURAI_USB_INPUT=m\nCONFIG_BATTERY_SAMURAI_GAUGE_PROTECTION=m\n'
(ref/'kernel-config.fragment').write_text(config)
result={'source_checkout_modified':False,'patch_applied':False,
    'patch_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':list(changes),
    'note':'Maintained Kconfig/DTS export. Running modules were built in the isolated intree view; no shared checkout mutation.'}
(ref/'kernel-integration-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
