from pathlib import Path
import json,struct
from gw1_data import Description
import host
d=Description('sunny')
w=d.words(d.uid('sensorDriverData'))
data=json.loads((host.PRIVATE.parent/'kernel270/gw1-sunny-direct-registers-private.json').read_text())
print('minimum_exposure_lines',d.words(w[49],'minLineCount'))
print('init',[(hex(r['address']),r['operation'],len(r['values']),r['values'][:1],r['delays_us']) for r in data['init']])
for i in [2,4]:
 regs=data['modes'][i]
 print('mode',i,'ops',{op:sum(r['operation']==op for r in regs) for op in ['WRITE','WRITE_BURST','WRITE_SEQUENTIAL']})
 print('timing',[(hex(r['address']),r['values'],r['delays_us']) for r in regs if 0x300<=r['address']<=0x31e or r['address'] in [0x100,0x101,0x202,0x204,0x340,0x342,0x344,0x346,0x348,0x34a,0x34c,0x34e,0x350,0x352,0x400,0x408,0x40a,0x40c,0x40e,0x900]])
 print('delays',[(n,r['delays_us']) for n,r in enumerate(regs) if any(r['delays_us'])])
W=Path('/home/cy122/x2pro-linux/camera270-kernel')
p=W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
lines=p.read_text().splitlines()
for term,before,after in [('cam_pmic_q:',4,48),('s5k3m5-samurai',3,3),('&cci0_i2c0',1,10),('cam_front_reset:',2,12)]:
 for n,l in enumerate(lines):
  if term in l:print('\n'.join(lines[max(0,n-before):n+after]))
print('cci_check')
for file in ['drivers/i2c/busses/i2c-qcom-cci.c','drivers/media/platform/qcom/camss/camss.c','drivers/media/v4l2-core/v4l2-fwnode.c']:
 lines=(W/file).read_text().splitlines()
 for n,l in enumerate(lines):
  if 'max_write_len' in l or ('CPHY' in l and file.endswith('camss.c')):
   print(file,n+1,'\n'.join(lines[max(0,n-2):n+5]))
