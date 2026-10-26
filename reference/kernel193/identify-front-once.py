from pathlib import Path
import ctypes,dbus,errno,fcntl,hashlib,json,os,struct,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k193-front-identify';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k193-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and Path('/sys/module/samurai_cci_bringup').is_dir() and not Path('/sys/module/samurai_front_identify').exists()
cci=Path('/sys/bus/i2c/devices/i2c-7');assert (cci/'of_node').resolve().as_posix().endswith('/cci@ac4b000/i2c-bus@1')
assert all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5])
info=json.loads((root/'k193-tools/front-helper-build-validation.json').read_text());candidate=root/'k193-tools/samurai-front-identify-k193-private.ko';assert hashlib.sha256(candidate.read_bytes()).hexdigest()==info['candidate_sha256']
regulators=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if not (p/'name').is_file() or (p/'name').read_text().strip() not in ['ldo1','smps8']:continue
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 regulators.append(dict(sysfs=p.name,name=(p/'name').read_text().strip(),of_path=str(node.resolve()),voltage=int((p/'microvolts').read_text()),users=int((p/'num_users').read_text())))
assert len([r for r in regulators if r['name']=='ldo1' and r['voltage']==1800000 and r['of_path'].endswith('/regulators-1/ldo1') and r['users']==0])==1
assert len([r for r in regulators if r['name']=='smps8' and r['voltage']==1352000 and r['users']==3])==1
assert all(r['voltage']==752000 for r in regulators if r['name']=='ldo1' and not r['of_path'].endswith('/regulators-1/ldo1'))
def gpio_snapshot():
 chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve().name=='pinctrl@3100000'];assert len(chips)==1
 fd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);result=[]
 try:
  for offset in [12,15,29]:
   meta=bytearray(256);struct.pack_into('I',meta,64,offset);fcntl.ioctl(fd,0xc100b405,meta,True);assert struct.unpack_from('Q',meta,72)[0]==4 and not bytes(meta[32:64]).rstrip(b'\0')
   req=bytearray(592);struct.pack_into('I',req,0,offset);struct.pack_into('I',req,560,1);fcntl.ioctl(fd,0xc250b407,req,True);line=struct.unpack_from('i',req,588)[0]
   try:
    data=bytearray(struct.pack('QQ',0,1));fcntl.ioctl(line,0xc010b40e,data,True);value=struct.unpack_from('Q',data)[0]&1
   finally:os.close(line)
   result.append(dict(offset=offset,flags=4,value=value))
 finally:os.close(fd)
 return result
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('length',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Rdwr(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
def pmic_snapshot():
 fd=os.open('/dev/i2c-1',os.O_RDWR|os.O_CLOEXEC)
 def read(address,reg,count):
  tx=(ctypes.c_uint8*2)(reg>>8,reg&255);rx=(ctypes.c_uint8*count)();msgs=(Msg*2)(Msg(address,0,2,tx),Msg(address,1,count,rx));request=Rdwr(msgs,2);assert fcntl.ioctl(fd,0x0707,request)==2;return list(rx)
 try:return dict(identity=read(4,0x0100,6),sid=read(4,0x0644,1),chip_enable=read(4,0x0950,1),ldos=[dict(index=i+1,voltage=read(5,0x4040+i*0x100,2),enable=read(5,0x4046+i*0x100,1),status=read(5,0x4008+i*0x100,1)) for i in range(7)])
 finally:os.close(fd)
before=dict(gpios=gpio_snapshot(),pmic=pmic_snapshot(),regulators=regulators)
assert all(r['value']==0 for r in before['gpios']) and all(r['enable']==[0] for r in before['pmic']['ldos'])
(out/'before-private.json').write_text(json.dumps(before,indent=2))
log_before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(log_before)
clocks=Path('/sys/kernel/debug/clk/clk_summary');(out/'clocks-before-private.txt').write_bytes(clocks.read_bytes())
with (out/'insmod-private.log').open('xb') as log:
 proc=subprocess.Popen(['insmod',str(candidate)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);(out/'loader-pid-private.txt').write_text(str(proc.pid))
 try:proc.wait(timeout=15)
 except subprocess.TimeoutExpired:
  print(json.dumps(dict(stage=193,loader_running=True,do_not_reload=True)));raise SystemExit(0)
values={}
param=Path('/sys/module/samurai_front_identify/parameters')
if param.is_dir():values={p.name:int(p.read_text()) for p in param.iterdir()}
after=dict(gpios=gpio_snapshot(),pmic=pmic_snapshot());(out/'after-private.json').write_text(json.dumps(after,indent=2));(out/'clocks-after-private.txt').write_bytes(clocks.read_bytes())
log_after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(log_after)
report=dict(stage=193,insmod_exit=proc.returncode,module_parameters=values,gpio_directions_and_levels_restored=after['gpios']==before['gpios'],pmic_entire_sample_restored=after['pmic']==before['pmic'],taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta={k:log_after.count(v)-log_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert proc.returncode==0 and report['gpio_directions_and_levels_restored'] and report['pmic_entire_sample_restored'] and values.get('restore_result')==0
assert report['taint']==0 and all(v==0 for v in report['fault_delta'].values())
