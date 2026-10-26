"""Read the specified EEPROM twice while a normal V4L2 client owns its power."""
from pathlib import Path
import ctypes,fcntl,hashlib,json,os,re,signal,subprocess,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai/k299-eeprom-r1');assert not root.exists();root.mkdir(mode=0o700)
state=dict(stage=299,terminal=False,phase='preflight',pid=os.getpid())
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def health():
 sensors={}
 for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
  for p in Path('/sys/bus/i2c/drivers',driver).glob('*'):
   if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name):sensors[driver]=(p/'power/runtime_status').read_text().strip()
 rails={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-front-','cam-rear-','cam-tele-','cam-main-')):rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
 return dict(sensor_pm=sensors,rails=rails,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('len',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Transfer(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
save();child=None;fd=None;error=None;reads=[];ret=None;before=None;faults={};hold_log=None
dmesg_before=subprocess.check_output(['dmesg'])
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes() and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k298+'
 before=health();assert len(before['sensor_pm'])==5 and all(v=='suspended' for v in before['sensor_pm'].values()) and len(before['rails'])==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in before['rails'].values()) and not before['taint']
 bound=[p for p in Path('/sys/bus/i2c/drivers/imx319').glob('*') if p.is_symlink() and re.fullmatch(r'\d+-0010',p.name)];assert len(bound)==1
 bus=int(bound[0].name.split('-')[0]);assert not Path('/sys/bus/i2c/devices',f'{bus}-0051').exists()
 dev=Path('/dev')/f'i2c-{bus}';assert dev.is_char_device() and os.major(dev.stat().st_rdev)==89
 (root/'graph-before-private.txt').write_bytes(subprocess.check_output(['media-ctl','-d','/dev/media0','-p']))
 dmesg_before=subprocess.check_output(['dmesg']);(root/'dmesg-before-private.txt').write_bytes(dmesg_before)
 hold_log=(root/'hold-private.log').open('xb')
 child=subprocess.Popen(['/var/lib/samurai/k299-tools/calibration-hold','--hold',str(root/'not-saved')],stdin=subprocess.DEVNULL,stdout=hold_log,stderr=hold_log)
 state.update(phase='waiting_for_standard_stream',child_pid=child.pid,child_start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
 deadline=time.monotonic()+6
 while time.monotonic()<deadline:
  assert child.poll() is None,'Power-owner capture exited before EEPROM reads'
  logbytes=(root/'hold-private.log').read_bytes()
  if b'STREAMON_OK' in logbytes and b'FRAME number=' in logbytes and (bound[0]/'power/runtime_status').read_text().strip()=='active':break
  time.sleep(.05)
 else:raise TimeoutError('Standard stream did not become active')
 fd=os.open(dev,os.O_RDWR|os.O_CLOEXEC);funcs=ctypes.c_ulong();fcntl.ioctl(fd,0x0705,funcs);assert funcs.value&1
 deadline=time.monotonic()+20
 def read_range(start,length):
  out=bytearray()
  for offset in range(start,start+length,8):
   assert child.poll() is None,'Power-owner capture exited during read'
   if time.monotonic()>deadline:raise TimeoutError('Bounded EEPROM read deadline')
   count=min(8,start+length-offset);assert 0<=offset<12287 and offset+count<=12287
   pointer=(ctypes.c_uint8*2)(offset>>8,offset&255);value=(ctypes.c_uint8*count)()
   # The first message contains only the 16-bit address pointer, never EEPROM data.
   messages=(Msg*2)(Msg(0x51,0,2,pointer),Msg(0x51,1,count,value));transfer=Transfer(messages,2)
   assert fcntl.ioctl(fd,0x0707,transfer)==2
   out.extend(value)
  return bytes(out)
 state.update(phase='reading_known_source_address');save()
 a=read_range(0,32);b=read_range(0,32);assert a==b and a not in [bytes(32),bytes([255])*32]
 for index in [1,2]:
  data=read_range(0,12287);assert data[:32]==a
  (root/f'eeprom-read{index}-private.bin').write_bytes(data);reads.append(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 assert reads[0]==reads[1]
 state.update(phase='reads_complete');save()
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if fd is not None:os.close(fd)
 if child is not None:
  if child.poll() is None:child.send_signal(signal.SIGINT)
  try:ret=child.wait(timeout=8)
  except subprocess.TimeoutExpired:state.update(phase='stream_cleanup_pending');save()
 if hold_log is not None:hold_log.close()
 time.sleep(1)
after=health();text=(root/'hold-private.log').read_text(errors='replace') if (root/'hold-private.log').exists() else ''
dmesg_after=subprocess.check_output(['dmesg']);(root/'dmesg-after-private.txt').write_bytes(dmesg_after)
if before is not None:
 faults={k:dmesg_after.count(v)-dmesg_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
graph=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(root/'graph-after-private.txt').write_bytes(graph)
restored=(root/'graph-before-private.txt').exists() and graph==(root/'graph-before-private.txt').read_bytes()
report=dict(stage=299,kernel_build=298,read_bytes=12287,reads=reads,duplicate_reads_equal=len(reads)==2 and reads[0]==reads[1],tool_exit=ret,power_owner_still_live=child is not None and child.poll() is None,
 actual_frames=len(re.findall(r'^FRAME ',text,re.M)),statistics_frames=0,graph_restored=restored,before=before,after=after,fault_delta=faults,
 standard_stream_owns_power=True,no_eeprom_data_writes=True,no_calibration_applied=True,calibration_checksum_and_full_layout_not_verified=True,
 private_raw_data_preserved=True,error=error,passed=error is None and ret==0 and restored and before==after and not any(faults.values()) and 'CAPTURE_RESULT success=1 cleanup_complete=1' in text)
(root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');state.update(terminal=True,phase='finished' if report['passed'] else 'failed',exit_code=0 if report['passed'] else 1);save()
