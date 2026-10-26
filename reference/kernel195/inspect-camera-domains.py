from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
found=0
for p in sorted((k/'arch/arm64/boot/dts/qcom').glob('*.dts*')):
 lines=p.read_text().splitlines()
 for i,line in enumerate(lines):
  if 'power-domains' in line and 'TITAN' in line:
   text='\n'.join(lines[max(0,i-15):min(len(lines),i+6)])
   if any(x in text for x in ['camera@','sensor@','imx','ov','s5k']):print(p.name,text);found+=1
 if found>10:break
for name in ['Documentation/devicetree/bindings/media/video-interface-devices.yaml','Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml','drivers/i2c/busses/i2c-qcom-cci.c']:
 s=(k/name).read_text();lines=s.splitlines();print(name)
 for i,line in enumerate(lines):
  if 'power-domains' in line or 'ignore_children' in line:print('\n'.join(lines[max(0,i-3):i+6]))
