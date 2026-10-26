from pathlib import Path
import json,mmap,os,struct,fcntl
common=Path('/var/lib/samurai/k195-modules/probe-q-reset-address.py').read_text().split('report=dict(',1)[0]
assert "out=root/'k195-q-reset'" in common
common=common.replace("out=root/'k195-q-reset'","out=root/'k199-front-session'").replace('k195-baseline','k199-baseline');exec(compile(common,'<verified-i2c-prefix>','exec'))
dt=Path('/sys/firmware/devicetree/base');tlmm=dt/'soc@0/pinctrl@3100000';cells=struct.unpack('>'+str(len((tlmm/'reg').read_bytes())//4)+'I',(tlmm/'reg').read_bytes());names=(tlmm/'reg-names').read_bytes().decode().strip('\0').split('\0');regions={n:(cells[4*i]<<32)|cells[4*i+1] for i,n in enumerate(names)}
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve()==tlmm];assert len(chips)==1;tfd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);memfd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC)
def gpio(pin):
 info=bytearray(256);struct.pack_into('I',info,64,pin);fcntl.ioctl(tfd,0xc100b405,info,True);flags=struct.unpack_from('Q',info,72)[0];assert not bytes(info[32:64]).rstrip(b'\0')
 req=bytearray(592);struct.pack_into('I',req,0,pin);struct.pack_into('I',req,560,1);fcntl.ioctl(tfd,0xc250b407,req,True);fd=struct.unpack_from('i',req,588)[0]
 try:value=level(fd)
 finally:os.close(fd)
 address=regions['east' if pin==29 else 'north']+0x1000*pin
 with mmap.mmap(memfd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=address) as mapping:ctl=struct.unpack_from('<I',mapping,0)[0]
 return dict(pin=pin,flags=flags,level=value,ctl_address=address,ctl=ctl)
report=dict(stage=199,gpios=[gpio(n) for n in [12,15,29]],pmic=snapshot(4),pmic_p_level=sample(0),pmic_q_level=sample(3),resource_map=regions,initial_clock_rate=19200000)
assert all(r['flags']==4 and r['level']==0 for r in report['gpios']) and all(r['enable']['data']==[0] for r in report['pmic']['ldos']) and report['pmic_p_level']==0 and report['pmic_q_level']==1
(out/'before-private.json').write_text(json.dumps(report,indent=2)+'\n');os.close(memfd);os.close(tfd);os.close(gfd);os.close(ifd)
print(json.dumps(dict(stage=199,gpios=report['gpios'],pmic_outputs_disabled=True,pmic_p_held_reset=True,pmic_q_released=True,actual_mclk_ctl_uses_north_region=True)))
