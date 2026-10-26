"""Add the GW1 candidate to a new branch; no phone or old build mutations."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent
W=Path('/home/cy122/x2pro-linux/camera270-kernel')
assert not subprocess.check_output(['git','status','--porcelain'],cwd=W)
base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()
assert base=='ac7ccc2da924b44aa6dff5d1be24356253890ee8'
subprocess.run(['git','switch','-c','samurai-main-camera272'],cwd=W,check=True)
mapping={
 's5kgw1.c':'drivers/media/i2c/s5kgw1.c',
 's5kgw1-tables.h':'drivers/media/i2c/s5kgw1-tables.h',
 'samsung,s5kgw1.yaml':'Documentation/devicetree/bindings/media/i2c/samsung,s5kgw1.yaml',
 's5kgw1-samurai.dtsi':'arch/arm64/boot/dts/qcom/s5kgw1-samurai.dtsi',
}
for source,dest in mapping.items():
 assert not (W/dest).exists()
 shutil.copyfile(R/source,W/dest)
p=W/'drivers/media/i2c/Kconfig';text=p.read_text()
marker='config VIDEO_S5K3M5\n';assert text.count(marker)==1
addition='''config VIDEO_S5KGW1
	tristate "Samsung S5KGW1 sensor support"
	depends on I2C
	select V4L2_CCI_I2C
	help
	  V4L2 support for the Samsung S5KGW1 RAW10 camera sensor with
	  a 19.2 MHz input clock and a three-trio MIPI C-PHY interface.

'''
p.write_text(text.replace(marker,addition+marker))
p=W/'drivers/media/i2c/Makefile';text=p.read_text();marker='obj-$(CONFIG_VIDEO_S5K3M5)'
assert text.count(marker)==1
text=text.replace(marker,'obj-$(CONFIG_VIDEO_S5KGW1) += s5kgw1.o\n'+marker)
p.write_text(text)
p=W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
text=p.read_text();assert '#include "s5kgw1-samurai.dtsi"' not in text
p.write_text(text+'\n#include "s5kgw1-samurai.dtsi"\n')
report=dict(stage=272,base_commit=base,branch='samurai-main-camera272',
 sources={dest:hashlib.sha256((W/dest).read_bytes()).hexdigest() for dest in mapping.values()},
 phone_unchanged=True,not_yet_compiled=True,not_yet_probed=True)
(R/'driver-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
