from pathlib import Path
import re,subprocess,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'drivers/media/i2c/imx471.c'
lines=p.read_text().splitlines()
for i,s in enumerate(lines):
 if any(x in s for x in ['static int imx471_power','static void imx471_power','static int imx471_parse','static int imx471_probe','imx471_of','ACPI_PTR','xvclk','xclk','supplies','19200000','24000000','CHIP_ID']):
  print(i+1,'\n'.join(lines[max(0,i-2):min(len(lines),i+23)]))
cfg=(k/'.config').read_text().splitlines()
print('\n'.join(s for s in cfg if any(x in s for x in ['VIDEO_IMX471','QCOM_CCI','MFD_QCOM_PM8008','REGULATOR_QCOM_PM8008','VIDEO_IMX319'])))
print('source status',subprocess.check_output(['git','status','--short'],cwd=k,text=True))
