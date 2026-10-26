from pathlib import Path
import fcntl,json,mmap,os,struct,subprocess
root=Path('/var/lib/samurai');out=root/'k200-front-capture-r1'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
r=json.loads((out/'summary.json').read_text());assert r['physical_image_capture'] and not any(r['fault_delta'].values()) and not r['pins_restored_exact']
assert [(g['pin'],g['ctl']) for g in r['before']['gpios']]==[(12,1),(15,1),(29,1)]
assert all(not Path('/sys/module/'+n).exists() for n in ['imx471','samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','i2c_qcom_cci'])
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines();rows=[l.split() for l in clocks if 'cam_cc_mclk2_clk ' in l];assert len(rows)==1 and rows[0][1:4]==['0','0','0'] and 'N' in rows[0]
node=Path('/sys/firmware/devicetree/base/soc@0/pinctrl@3100000');chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve()==node];assert len(chips)==1
fd=os.open('/dev/'+chips[0].name,os.O_RDONLY);info=bytearray(256);struct.pack_into('I',info,64,15);fcntl.ioctl(fd,0xc100b405,info,True);os.close(fd)
assert struct.unpack_from('Q',info,72)[0]==4 and not bytes(info[32:64]).rstrip(b'\0')
assert r['before']['gpios'][1]['ctl_address']==0x0390f000
mem=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)
try:
 with mmap.mmap(mem,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE,offset=0x0390f000) as region:
  before=struct.unpack_from('<I',region,0)[0];input_data=struct.unpack_from('<I',region,4)[0]
  assert before==0 and input_data&1==0
  restored=(before & ~3) | (r['before']['gpios'][1]['ctl'] & 3)
  struct.pack_into('<I',region,0,restored);after=struct.unpack_from('<I',region,0)[0];assert after==1 and struct.unpack_from('<I',region,4)[0]&1==0
finally:os.close(mem)
result=dict(stage=200,original_capture_cleanup_check_failed=True,physical_frame_count=6,
 gpio_v2_bias_request_accepted_but_hardware_unchanged=True,original_pull_restored_by_one_masked_mmio_write=True,
 register=0x0390f000,mask=3,before=before,after=after,input_stayed_low=True,mclk_disabled_and_gpio_unclaimed=True,
 next_overlay_sleep_bias_will_preserve_original_pull=True)
(out/'bias-restoration.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
