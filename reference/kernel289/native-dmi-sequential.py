"""One bounded internal TPG capture with LUT readback and resource recovery."""
from pathlib import Path
import json,os,re,signal,subprocess,time,traceback

root=Path('/var/lib/samurai/k289-dmi-r2');assert not root.exists();root.mkdir(mode=0o700)
state=dict(stage=289,terminal=False,phase='preflight',pid=os.getpid())
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
save();child=None
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k288-work/boot-id-private.txt').read_bytes()
 assert os.uname().version.startswith('#288 ')
 before=health();assert len(before['sensor_pm'])==5 and all(v=='suspended' for v in before['sensor_pm'].values()) and before['taint']==0
 assert len(before['rails'])==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in before['rails'].values())
 dmesg_before=subprocess.check_output(['dmesg']);(root/'dmesg-before-private.txt').write_bytes(dmesg_before)
 graph_before=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(root/'graph-before-private.txt').write_bytes(graph_before)
 log=root/'capture-private.log'
 with log.open('xb') as output:
  child=subprocess.Popen(['/var/lib/samurai/k289-tools/dmi-sequential','--capture',str(root/'first-nv12-private.raw')],stdout=output,stderr=subprocess.STDOUT)
  state.update(phase='capturing',child_pid=child.pid);save()
  try:ret=child.wait(timeout=25)
  except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=6)
 time.sleep(1)
 after=health();dmesg_after=subprocess.check_output(['dmesg']);(root/'dmesg-after-private.txt').write_bytes(dmesg_after)
 graph_after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(root/'graph-after-private.txt').write_bytes(graph_after)
 text=log.read_text(errors='replace')
 faults={k:dmesg_after.count(v)-dmesg_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
 report=dict(stage=289,tool_exit=ret,tool_output=text,before=before,after=after,fault_delta=faults,
  actual_frames=len(re.findall(r'^FRAME ',text,re.M)),graph_restored=graph_before==graph_after,hardware_isp_complete=False)
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(terminal=True,phase='finished',exit_code=ret);save()
except BaseException:
 if child and child.poll() is None:
  child.send_signal(signal.SIGINT)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:pass
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(terminal=True,phase='failed',exit_code=1);save()
