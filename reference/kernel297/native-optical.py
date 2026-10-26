"""Run one physical IMX319 hardware PIX exposure sweep and preserve actual outcome."""
from pathlib import Path
import json,os,re,signal,subprocess,time,traceback
root=Path('/var/lib/samurai/k297-optical-r1');assert not root.exists();root.mkdir(mode=0o700)
state=dict(stage=297,terminal=False,phase='preflight',pid=os.getpid())
def save():
 p=root/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'state-private.json')
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
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k297-work/boot-id-private.txt').read_bytes()
 assert os.uname().version.startswith('#297 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k297+'
 before=health();assert len(before['sensor_pm'])==5 and all(v=='suspended' for v in before['sensor_pm'].values())
 assert before['taint']==0 and all(v['state']=='disabled' and v['num_users']=='0' for v in before['rails'].values())
 dmesg_before=subprocess.check_output(['dmesg']);(root/'dmesg-before-private.txt').write_bytes(dmesg_before)
 (root/'graph-before-private.txt').write_bytes(subprocess.check_output(['media-ctl','-d','/dev/media0','-p']))
 log=root/'capture-private.log'
 with log.open('xb') as output:
  child=subprocess.Popen(['/var/lib/samurai/k297-tools/optical','--capture',str(root/'frame-private')],stdout=output,stderr=subprocess.STDOUT)
  state.update(phase='capturing',child_pid=child.pid);save()
  try:ret=child.wait(timeout=25)
  except subprocess.TimeoutExpired:
   child.send_signal(signal.SIGINT);state.update(phase='interrupt_sent');save();ret=child.wait(timeout=6)
 time.sleep(1)
 after=health();dmesg_after=subprocess.check_output(['dmesg']);(root/'dmesg-after-private.txt').write_bytes(dmesg_after)
 (root/'graph-after-private.txt').write_bytes(subprocess.check_output(['media-ctl','-d','/dev/media0','-p']))
 text=log.read_text(errors='replace')
 faults={k:dmesg_after.count(v)-dmesg_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
 images={}
 for frame in root.glob('*.nv12'):
  b=frame.read_bytes();assert len(b)==115200;y=b[:76800];uv=b[76800:]
  images[frame.name]=dict(bytes=len(b),y_min=min(y),y_max=max(y),y_mean=sum(y)/len(y),uv_min=min(uv),uv_max=max(uv),uv_mean=sum(uv)/len(uv))
 report=dict(stage=297,kernel_build=297,physical_sensor='imx319',sensor_and_csid_tpg_disabled=True,
             standard_mc_v4l2_only=True,no_userspace_mmio=True,no_cpu_isp=True,tool_exit=ret,tool_output=text,
             before=before,after=after,fault_delta=faults,actual_frames=len(re.findall(r'^FRAME ',text,re.M)),images=images,
             graph_restored=(root/'graph-before-private.txt').read_bytes()==(root/'graph-after-private.txt').read_bytes(),
             hardware_isp_complete=False)
 report['statistics']=[dict((k,int(v,16) if k=='hash' else int(v)) for k,v in re.findall(r'(\w+)=([0-9a-f]+)',line)) for line in text.splitlines() if line.startswith('STATS frame=')]
 report['statistics_frames']=len(report['statistics'])
 report['passed']=report['statistics_frames']==18 and ret==0 and report['actual_frames']==18 and report['graph_restored'] and not any(faults.values()) and before==after
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');state.update(terminal=True,phase='finished',exit_code=ret);save()
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(terminal=True,phase='failed',exit_code=1);save()
