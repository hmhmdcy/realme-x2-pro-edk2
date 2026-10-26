from pathlib import Path
import subprocess, struct, json
root=Path('/mnt/e/edk2-samurai-out/kernel117')
binary=root/'CamxChi/chi-cdk/tools/buildbins/linux64/ParameterParser'
symbols=subprocess.check_output(['nm','-C',str(binary)],text=True)
chosen=[s for s in symbols.splitlines() if 'BinaryFileFormat::' in s or 'BinaryParameter' in s]
out=Path('/mnt/e/edk2-samurai-out/kernel192')
(out/'parser-symbols-private.txt').write_text('\n'.join(chosen)+'\n')
print('\n'.join(chosen)[:13000])
binpath=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin')
b=binpath.read_bytes()
for i in range(0,min(len(b),0x700),16):
 data=b[i:i+16]
 print(f'{i:06x} {data.hex(" "):48} '+''.join(chr(x) if 32<=x<127 else '.' for x in data))
for p in (root/'CamxChi/chi-cdk/api/sensor').glob('*.xsd'):
 if p.name!='camxsensordriver.xsd':continue
 lines=p.read_text().splitlines()
 for i,s in enumerate(lines):
  if any(t in s for t in ['sensorDriverData','sensorSlaveAddress','powerUpSequence','powerDownSequence','slaveInfo']):
   print(p.name,i+1,'\n'.join(lines[max(0,i-2):i+15]))
