from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name,pattern,before,after in [('drivers/regulator/core.c','static struct regulator_dev *regulator_dev_lookup',0,180),('drivers/regulator/core.c','int regulator_register_supply_alias(',10,40),('drivers/regulator/core.c','static int set_consumer_device_supply(',5,65),('drivers/media/i2c/imx471.c','static int imx471_probe(',0,130)]:
 lines=(k/name).read_text().splitlines();matches=[i for i,line in enumerate(lines) if pattern in line];print(name,pattern)
 for i in matches:print('\n'.join(f'{j+1}: {lines[j]}' for j in range(max(0,i-before),min(len(lines),i+after))))
print('exports', '\n'.join(l for l in (k/'Module.symvers').read_text().splitlines() if 'regulator' in l and any(v in l for v in ['alias','of_get','get_by','supply','register'])))
