from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
paths=['arch/arm64/boot/dts/qcom/sm8150-samurai.dts','drivers/media/i2c/imx471.c','drivers/mfd/qcom-pm8008.c','drivers/i2c/busses/i2c-qcom-cci.c']
files={name:dict(exists=(k/name).is_file(),sha256=hashlib.sha256((k/name).read_bytes()).hexdigest() if (k/name).is_file() else None) for name in paths}
text=(k/'.config').read_text();settings={}
for name in ['CONFIG_VIDEO_IMX471','CONFIG_V4L2_CCI','CONFIG_V4L2_CCI_I2C','CONFIG_MFD_QCOM_PM8008','CONFIG_REGULATOR_QCOM_PM8008','CONFIG_I2C_QCOM_CCI','CONFIG_OF_OVERLAY']:
    found=re.search(r'^'+name+r'=(\S+)$',text,re.M);settings[name]=found[1] if found else 'not_enabled'
for name,value in re.findall(r'^(CONFIG_[A-Z0-9_]*(?:CCI|IMX471|PM8008)[A-Z0-9_]*)=(\S+)$',text,re.M):settings[name]=value
board=(k/paths[0]).read_text()
report=dict(stage=209,read_only_source_inventory=True,files=files,configuration=settings,
    board_declares_imx471='sony,imx471' in board,board_declares_pm8008='qcom,pm8008' in board,
    modules_order_contains_imx471='imx471.ko' in (k/'modules.order').read_text(),
    camera_makefile_lines=[line for line in (k/'drivers/media/i2c/Makefile').read_text().splitlines() if any(name in line for name in ['IMX471','V4L2_CCI'])])
(here/'camera-source-inventory-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
