from pathlib import Path
import difflib, gzip, hashlib, json, subprocess, shutil
r=Path('/mnt/e/edk2-samurai-out/kernel71')
w=Path('/mnt/e/RealmeX2Pro edk2')
k=Path('/home/cy122/x2pro-linux/linux')
stock=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
sources={}
items=[('stock-s3706-driver','drivers/input/touchscreen/oppo_touchscreen/Synaptics/S3706/synaptics_drivers_s3706.c'),
 ('stock-s3706-header','drivers/input/touchscreen/oppo_touchscreen/Synaptics/S3706/synaptics_s3706.h'),
 ('stock-touch-common','drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c'),
 ('stock-19781-pinctrl','arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi'),
 ('stock-19781-mtp','arch/arm64/boot/dts/19781/sm8150-mtp.dtsi')]
for name,rel in items:
 data=subprocess.check_output(['git','--git-dir='+str(stock),'show',commit+':'+rel])
 (r/(name+'.source.gz')).write_bytes(gzip.compress(data,mtime=0))
 sources[name]=dict(commit=commit,path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
for name,rel in [('rmi-driver','drivers/input/rmi4/rmi_driver.c'),
 ('rmi-f12','drivers/input/rmi4/rmi_f12.c'),('rmi-binding','Documentation/devicetree/bindings/input/syna,rmi4.yaml'),
 ('sm8150-soc','arch/arm64/boot/dts/qcom/sm8150.dtsi')]:
 data=(k/rel).read_bytes();(r/(name+'.source.gz')).write_bytes(gzip.compress(data,mtime=0))
 sources[name]=dict(path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
sources['reset-patch']=dict(url='https://lists.openwall.net/linux-kernel/2026/09/12/719',
 message_id='20260912-rmi4-reset-v1-1-4a3fc8856830@protonmail.com',author='Roman Vivchar',
 status='proposed public patch; adapted locally, not claimed merged upstream',
 adaptations=['assert reset on devres cleanup/suspend','invalidate cached I2C page after hardware reset','dev_err_probe on GPIO lookup'])
(r/'source-origins.json').write_text(json.dumps(sources,indent=2)+'\n')
patches=[('rmi_i2c-before.c','rmi_i2c-after.c','drivers/input/rmi4/rmi_i2c.c','0007-input-rmi4-optional-reset-gpio.patch',
 'Input: rmi4: use optional reset GPIO and clean up power\n\nAdapt Roman Vivchar\'s proposed 20260912 reset GPIO patch; additionally\nassert reset on devres cleanup and invalidate the page cache after reset.\nSource: https://lists.openwall.net/linux-kernel/2026/09/12/719\nNo firmware flashing support is enabled.\n'),
 ('samurai-before.dts','samurai-after.dts','arch/arm64/boot/dts/qcom/sm8150-samurai.dts','0008-arm64-dts-samurai-s3706-touch.patch',
 'arm64: dts: samurai: enable board-native S3706 touch\n\nUse the RMX1931 19781 vendor/live wiring: I2C17, TLMM122 IRQ, TLMM54\nreset, PM8150 L17 at 3.0V and PM8150L GPIO5 active-high VIO enable.\nEnable QUP2/GPI DMA2 without changing DMA masks or other bus engines.\nThe generic RMI compatible is intentional; hardware identifies S3706A.\n')]
for before,after,rel,name,header in patches:
 diff=''.join(difflib.unified_diff((r/before).read_text().splitlines(True),(r/after).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
 (w/'linux-port/patches'/name).write_text('Subject: [PATCH] '+header+'\n'+diff)
 # Reverse-apply check in an isolated source layout; do not mutate live sources.
 layout=r/'patch-check'/rel
 layout.parent.mkdir(parents=True,exist_ok=True);layout.write_bytes((r/after).read_bytes())
 subprocess.run(['patch','--dry-run','-R','-p1','-i',str(w/'linux-port/patches'/name)],cwd=r/'patch-check',check=True,stdout=subprocess.PIPE)
shutil.copyfile(r/'samurai-after.dts',w/'linux-port/dts/sm8150-samurai.dts')
(w/'linux-port/kernel71-builtins.config').write_text('''# Add to the verified session67 configuration; retain actual initramfs/EUD.
CONFIG_I2C_QCOM_GENI=y
CONFIG_QCOM_GPI_DMA=y
CONFIG_RMI4_CORE=y
CONFIG_RMI4_I2C=y
CONFIG_RMI4_F12=y
# CONFIG_RMI4_F34 is not set
''')
print('Source snapshots, 0007/0008 patches, DTS and builtin fragment saved; reverse dry-run passes.')
