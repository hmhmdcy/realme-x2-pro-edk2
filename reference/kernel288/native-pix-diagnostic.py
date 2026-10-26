"""Snapshot bounded CSID/VFE registers only while the capture helper holds streaming."""
from pathlib import Path
import json,mmap,os,signal,struct,subprocess,time,traceback

base=(Path(__file__).parent/'native-pix-tpg.py').read_text()
base=base[:base.index('save()\ntry:')].replace('k288-tpg-r1','k288-tpg-r2')
exec(compile(base,'shared-tpg-health','exec'),globals())
save();child=None
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k288-work/boot-id-private.txt').read_bytes()
 assert os.uname().version.startswith('#288 ')
 before=health();assert len(before['sensor_pm'])==5 and all(v=='suspended' for v in before['sensor_pm'].values()) and before['taint']==0
 dmesg_before=subprocess.check_output(['dmesg']);(root/'dmesg-before-private.txt').write_bytes(dmesg_before)
 (root/'graph-before-private.txt').write_bytes(subprocess.check_output(['media-ctl','-d','/dev/media0','-p']))
 irqs=lambda:[l for l in Path('/proc/interrupts').read_text().splitlines() if 'csid' in l.lower() or 'vfe' in l.lower()]
 interrupts_before=irqs()
 log=root/'capture-private.log'
 with log.open('xb') as output:
  child=subprocess.Popen(['/var/lib/samurai/k288-tools/pix-tpg-diagnostic','--capture',str(root/'first-nv12-private.raw')],stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,env=dict(os.environ,SAMURAI_PIX_SNAPSHOT='1'))
  state.update(phase='waiting_for_stream',child_pid=child.pid);save()
  deadline=time.monotonic()+6
  while 'STREAMON_OK' not in log.read_text(errors='replace'):
   assert child.poll() is None,'Capture stopped before STREAMON'
   assert time.monotonic()<deadline,'No STREAMON handshake'
   time.sleep(0.05)
  state.update(phase='reading_active_registers');save()
  camss=next(p for p in Path('/sys/bus/platform/drivers/qcom-camss').iterdir() if p.is_symlink() and (p/'of_node/reg-names').exists())
  assert (camss/'power/runtime_status').read_text().strip()=='active' and child.poll() is None
  names=(camss/'of_node/reg-names').read_bytes().rstrip(b'\0').decode().split('\0')
  raw=(camss/'of_node/reg').read_bytes();assert len(raw)==16*len(names)
  regions={n:struct.unpack_from('>QQ',raw,16*i) for i,n in enumerate(names)}
  csid_offsets=[0x0,0x20,0x24,0x30,0x34,0x70,0x74,0x100,0x104,0x200,0x204,0x208,0x254,0x600,0x604,0x608,0x60c,0x610,0x614,0x618]
  vfe_offsets=[0x0,0x40,0x44,0x48,0x4c,0x50,0x5c,0x60,0x6c,0x70,0x7c,0x478,0x47c,0x488,0x48c,0x490,0x49c,0x4a0,0x4ac,0x6f8,0x6fc,0x700,0x704,0x798,0xc24,0xc28,0xce4,0xce8,0xe0c,0xe18,0xe1c,0xe2c,0xe38,0xe3c,0x200c,0x2010,0x2044,0x2048,0x204c,0x205c,0x2060,0x2064,0x2084]
  vfe_offsets+=list(range(0x560,0x57c,4))+list(range(0xa3c,0xa94,4))+list(range(0xf30,0xf60,4))
  vfe_offsets+=[0x2208+w*0x100+off for w in [3,4] for off in [0,12,16,20,24,28,32,60,64,68,72,76,80,84]]
  snapshots={}
  fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
  try:
   for name,offsets in [('csid0',csid_offsets),('vfe0',vfe_offsets)]:
    address,length=regions[name];assert 0xa000000<=address<0xb000000 and address%4096==0 and 0<length<=0x20000
    assert all(0<=o and o+4<=length for o in offsets) and child.poll() is None
    with mmap.mmap(fd,length,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=address) as memory:
     snapshots[name]={hex(o):hex(struct.unpack_from('<I',memory,o)[0]) for o in offsets}
  finally:os.close(fd)
  interrupts_active=irqs()
  assert child.poll() is None and (camss/'power/runtime_status').read_text().strip()=='active'
  (root/'register-snapshot-private.json').write_text(json.dumps(snapshots,indent=2)+'\n')
  child.stdin.write(b'G');child.stdin.flush();child.stdin.close()
  state.update(phase='capturing_after_snapshot');save()
  try:ret=child.wait(timeout=20)
  except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=6)
 time.sleep(1)
 after=health();dmesg_after=subprocess.check_output(['dmesg']);(root/'dmesg-after-private.txt').write_bytes(dmesg_after)
 graph_after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(root/'graph-after-private.txt').write_bytes(graph_after)
 text=log.read_text(errors='replace')
 faults={k:dmesg_after.count(v)-dmesg_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
 report=dict(stage=288,tool_exit=ret,tool_output=text,before=before,after=after,fault_delta=faults,registers=snapshots,
             interrupts_before=interrupts_before,interrupts_active=interrupts_active,
             read_only_mmio_while_stream_held=True,actual_frames=len(re.findall(r'^FRAME ',text,re.M)),
             graph_restored=(root/'graph-before-private.txt').read_bytes()==graph_after,hardware_isp_complete=False)
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(terminal=True,phase='finished',exit_code=ret);save()
except BaseException:
 if child and child.poll() is None:
  try:
   if child.stdin and not child.stdin.closed:child.stdin.write(b'G');child.stdin.flush();child.stdin.close()
   child.wait(timeout=20)
  except Exception:pass
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(terminal=True,phase='failed',exit_code=1);save()
