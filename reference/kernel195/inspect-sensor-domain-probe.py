from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');s=(k/'drivers/i2c/i2c-core-base.c').read_text();i=s.index('static int i2c_device_probe');b=s.index('static void i2c_device_remove',i);lines=s[i:b].splitlines()
for n,line in enumerate(lines):
 if any(x in line for x in ['dev_pm_domain','driver->probe','pm_runtime','i2c_of','of_clk']):print('\n'.join(lines[max(0,n-4):n+10]))
for p in (k/'Documentation/devicetree/bindings/media/i2c').glob('*.yaml'):
 if p.name.startswith(('sony,','ovti,')) and 'power-domains:' in p.read_text():
  print('binding with power-domains',p.name);break
