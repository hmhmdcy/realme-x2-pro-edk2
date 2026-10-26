from pathlib import Path
import gzip,json
names={'cci_read','cci_write','cci_multi_reg_write','devm_cci_regmap_init_i2c'}
symbols=[]
for line in Path('/proc/kallsyms').read_text().splitlines():
 parts=line.split()
 if len(parts)>=3 and parts[2] in names:symbols.append(dict(name=parts[2],type=parts[1],module=parts[3] if len(parts)>3 else None))
config=Path('/proc/config.gz');lines=gzip.decompress(config.read_bytes()).decode().splitlines() if config.exists() else []
print(json.dumps(dict(symbols=symbols,cci_module_dir=Path('/sys/module/v4l2_cci').exists(),config=[s for s in lines if 'CONFIG_V4L2_CCI' in s or 'CONFIG_VIDEO_IMX471' in s],module_files=[str(p) for p in Path('/usr/lib/modules').glob('*/kernel/drivers/media/v4l2-core/*cci*')])))
