"""Read active PLL/FLL/LLP registers and hardware timestamps; never save frames."""
from pathlib import Path
import host,json,sys

here=Path(__file__).resolve().parent
assert len(sys.argv) in [4,5]
width,height,vblank=map(int,sys.argv[1:4]);assert (width,height) in [(1928,1088),(2304,1728),(4608,3456)] and vblank in [-1,396]
attempt=sys.argv[4] if len(sys.argv)==5 else ''
assert attempt in ['', 'after-timing-fix']
tag=f'{width}x{height}-timing-vblank{vblank}'+('-'+attempt if attempt else '')
cell=2 if width==4608 else 1
code=(here/'native-mode-runner.py').read_text()
code=code.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'",'tag='+repr(tag))
code=code.replace("[(2304,1728,1)","[(1928,1088,1),(2304,1728,1)")
code=code.replace("names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern']","names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern','horizontal_blanking','pixel_rate','link_frequency']")
old="process=subprocess.Popen(['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)"
new="process=subprocess.Popen(['cam','--camera','/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10','--stream=role=raw,width='+str(width)+',height='+str(height),'--capture=120'],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)"
assert code.count(old)==1;code=code.replace(old,new)
marker="before=subprocess.check_output(['dmesg']);"
readers=r'''
import ctypes,statistics
subprocess.run(['modprobe','i2c-dev'],capture_output=True,check=True,timeout=15)
assert Path('/sys/bus/i2c/devices/7-0010/driver').resolve().name=='imx471'
assert Path('/sys/bus/i2c/devices/7-0010/of_node/compatible').read_bytes()==b'sony,imx471\0'
class I2cMsg(ctypes.Structure):
    _fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('length',ctypes.c_uint16),('buffer',ctypes.c_void_p)]
class I2cData(ctypes.Structure):
    _fields_=[('messages',ctypes.POINTER(I2cMsg)),('count',ctypes.c_uint32)]
libc=ctypes.CDLL(None,use_errno=True);libc.ioctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.POINTER(I2cData)];libc.ioctl.restype=ctypes.c_int
def read_register(address,length=1):
    # Two-message register-address/read transfer, no register-value writes.
    assert address in [0x0100,0x0114,0x0301,0x0303,0x0305,0x0306,0x0309,0x030b,0x030d,0x030e,0x0310,0x0340,0x0342]
    pointer=ctypes.create_string_buffer(address.to_bytes(2,'big'),2);value=ctypes.create_string_buffer(length)
    messages=(I2cMsg*2)(I2cMsg(0x10,0,2,ctypes.addressof(pointer)),I2cMsg(0x10,1,length,ctypes.addressof(value)))
    request=I2cData(messages,2);fd=os.open('/dev/i2c-7',os.O_RDWR|os.O_CLOEXEC)
    try:result=libc.ioctl(fd,0x0707,ctypes.byref(request));assert result==2,ctypes.get_errno()
    finally:os.close(fd)
    return int.from_bytes(value.raw,'big')
active_samples=[];register_errors=[]
'''
assert code.count(marker)==1;code=code.replace(marker,readers+'\n'+marker)
marker="    try:stdout,stderr=process.communicate(timeout=25)"
sampling=r'''
    try:
        if process.poll() is None and Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='active':
            assert read_register(0x0100)==1,'Sensor stream not yet active'
            if REQUESTED_VBLANK>=0:subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl=vertical_blanking='+str(REQUESTED_VBLANK)],capture_output=True,check=True,timeout=5)
            for _ in range(4):
                if process.poll() is not None:break
                registers={hex(address):read_register(address,2 if address in [0x0306,0x030e,0x0340,0x0342] else 1) for address in [0x0114,0x0301,0x0303,0x0305,0x0306,0x0309,0x030b,0x030d,0x030e,0x0310,0x0340,0x0342]}
                active_samples.append(dict(controls=controls(),registers=registers));time.sleep(0.08)
    except Exception as error:register_errors.append(repr(error))
'''.replace('REQUESTED_VBLANK',str(vblank))
assert code.count(marker)==1;code=code.replace(marker,sampling+'\n'+marker)
code=code.replace("data=json.loads(stdout) if process.returncode==0 else None",'''frames=[dict(timestamp=float(m[1]),sequence=int(m[2])) for m in re.finditer(r'^(\\d+\\.\\d+)\\s+\\([^\\n]+?seq:\\s*(\\d+)',stdout.decode(),re.M)]
data=dict(width=width,height=height,stride=None,frames=frames) if process.returncode==0 else None''')
code=code.replace("all_active_raw_pixels_examined=kind=='raw',raw_padding_excluded=kind=='raw'","all_active_raw_pixels_examined=False,raw_padding_excluded=False,raw_timing_only=True,active_samples=active_samples,register_errors=register_errors")
code=code.replace('dma_sync_read_start_end=True,','dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True,')
marker="(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(report))"
assert code.count(marker)==1
finish=r'''
assert data and len(frames)==120 and active_samples and not register_errors
assert re.search(r'configuring streams: \(0\) '+str(width)+'x'+str(height)+r'-SRGGB10_CSI2P',stderr.decode())
intervals=[(b['timestamp']-a['timestamp'])/(b['sequence']-a['sequence']) for a,b in zip(frames[-61:],frames[-60:])]
assert all(x>0 for x in intervals)
last=active_samples[-1];c=last['controls'];r=last['registers']
report.update(frame_count=120,fps_from_hardware_timestamps=1/statistics.median(intervals),
              fps_from_current_controls=c['pixel_rate']/((width+c['horizontal_blanking'])*(height+c['vertical_blanking'])),
              hardware_line_length=r['0x342'],hardware_frame_length=r['0x340'],
              inferred_rate_if_vt_four_pixel_lanes=19200000*r['0x306']/r['0x305']/r['0x303']/r['0x301']*4,
              sequence_deltas=[b['sequence']-a['sequence'] for a,b in zip(frames,frames[1:])])
'''
code=code.replace(marker,finish+'\n'+marker)
compile(code,'native-timing219','exec')
p=host.ssh('python3 - raw 0 '+str(width)+' '+str(height)+' '+str(cell)+' system',input=code.encode(),timeout=100)
(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(tag+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['frames','sequence_deltas','active_samples']}))
assert report['program_exit']==0 and report['all_formats_restored'] and report['media_graph_restored'] and report['sensor_controls_restored']
assert report['taint']==0 and not any(report['fault_delta'].values()) and report['camera_devices_suspended']
if attempt:
    assert abs(report['fps_from_current_controls']/report['fps_from_hardware_timestamps']-1)<0.001
