from pathlib import Path
import fcntl,json,mmap,os,struct,subprocess

root=Path('/var/lib/samurai');out=root/'k200-front-capture-r1'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
r=json.loads((out/'summary.json').read_text());assert r['physical_image_capture'] and r['taint']==0 and not r['pins_restored_exact'] and not any(r['fault_delta'].values())
assert all(not Path('/sys/module/'+n).exists() for n in ['imx471','samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','i2c_qcom_cci'])
expected=r['before']['gpios'];saved=r['gpios_after_restore']
assert [(g['pin'],g['ctl'],g['level']) for g in expected]==[(12,1,0),(15,1,0),(29,1,0)]
assert [(g['pin'],g['ctl'],g['level']) for g in saved]==[(12,1,0),(15,0,0),(29,1,0)]
node=Path('/sys/firmware/devicetree/base/soc@0/pinctrl@3100000')
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve()==node];assert len(chips)==1
gfd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);mfd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC)
def ctl(g):
 with mmap.mmap(mfd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=g['ctl_address']) as region:return struct.unpack_from('<I',region,0)[0]
g=expected[1];assert g['pin']==15 and g['ctl_address']==0x0390f000 and ctl(g)==0
info=bytearray(256);struct.pack_into('I',info,64,15);fcntl.ioctl(gfd,0xc100b405,info,True);assert struct.unpack_from('Q',info,72)[0]==4 and not bytes(info[32:64]).rstrip(b'\0')
request=bytearray(592);struct.pack_into('I',request,0,15)
# GPIO_V2_LINE_FLAG_INPUT | GPIO_V2_LINE_FLAG_BIAS_PULL_DOWN, uapi/linux/gpio.h.
struct.pack_into('Q',request,288,(1<<2)|(1<<9));struct.pack_into('I',request,560,1)
fcntl.ioctl(gfd,0xc250b407,request,True);fd=struct.unpack_from('i',request,588)[0]
try:
 value=bytearray(struct.pack('QQ',0,1));fcntl.ioctl(fd,0xc010b40e,value,True);assert struct.unpack_from('Q',value)[0]&1==0
 assert ctl(g)==g['ctl']
finally:os.close(fd)
after=[dict(pin=g['pin'],ctl=ctl(g),ctl_address=g['ctl_address']) for g in expected];assert all(a['ctl']==b['ctl'] for a,b in zip(after,expected));os.close(mfd);os.close(gfd)
final=dict(stage=200,physical_image_capture=True,physical_frame_count=6,capture_cycles=2,
    first_cleanup_pin_check_failed=True,reason='MCLK sleep bias-disable differed from fresh boot pull-down',
    gpio15_restored_via_standard_input_pull_down_request=True,all_three_pad_ctl_values_restored_exact=True,
    no_mmio_writes=True,after=after,fault_delta=r['fault_delta'],taint=0)
(out/'bias-restoration.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(final))
