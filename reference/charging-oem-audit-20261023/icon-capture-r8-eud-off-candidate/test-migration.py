"""Only new identity/entry/300-second host paths; all device boundaries fake."""
from pathlib import Path
import ast,base64,copy,hashlib,importlib.util,inspect,json,sys,tempfile,traceback,unittest
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
launcher=load(HERE/'launcher.py','r8_icon_launcher')
worker=load(HERE/'worker.py','r8_frozen_worker')
with patch.dict(sys.modules,{'worker':worker}):entry=load(HERE/'capture-entry.py','r8_capture_entry')
def ready(request):
 receipt={k:request[k] for k in ['transaction','token','expected_boot','manifest_sha256','files','argv']};receipt.update(pid=123,start_ticks=456)
 observations=[]
 for tick,boot in [(10,110.25),(12,112.45)]:
  status=dict(pid=123,start_ticks=456,active=True,terminal=False,phase='ready',ready_for_user_action=True,tick=tick,t=boot-100,
   realtime=boot+900-.25,remaining_boottime_seconds=request['max_seconds']+100-boot)
  observations.append(dict(status=status,process=dict(state='alive',pid=123,start_ticks=456,argv=request['argv']),remote_realtime=boot+900,remote_boottime=boot))
 return dict(identity_unchanged=True,launch_receipt=receipt,clock_start={'boot':100},observations=observations,host_roundtrip_seconds=2.3)
class FakeSSH:
 def __init__(self):self.calls=[]
 def __call__(self,command,**kw):
  r=json.loads(kw['input']);self.calls.append(r)
  if r['action']=='launch':value={'launched':True,'launch_receipt':ready(r)['launch_receipt']}
  elif r['action']=='status':value=ready(r)
  else:
   raw=b'{"retained":"original"}\n'
   value=dict(identity_unchanged=True,cleanup_state=dict(exact_worker_state='absent',worker_terminal=True,monitor_started=True,monitor_errors=[],dbus_returncode=-15),
    files={'capture/capture-private.json':dict(base64=base64.b64encode(raw).decode(),sha256=launcher.sha(raw))})
  return SimpleNamespace(returncode=0,stdout=json.dumps(value).encode(),stderr=b'')
class Migration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.pins=self.root/'pins.json'
  self.entries=json.loads(launcher.PINS.read_bytes())
  for n,e in self.entries.items():
   if n not in ['transport','key_transport']:
    p=self.root/(n+'.json');p.write_bytes(Path(e['path']).read_bytes());e['path']=str(p)
  self.pins.write_text(json.dumps(self.entries));self.migration=self.root/'migration.json'
  self.migration.write_text(json.dumps(dict(schema='charging-icon-r8-eud-off-migration-tests-v1',passed=True,
   launcher_sha256=launcher.sha((HERE/'launcher.py').read_bytes()),identity_pins_sha256=launcher.sha(self.pins.read_bytes()),sha256=launcher.FROZEN,manifest_sha256=launcher.MANIFEST)))
  self.ssh=FakeSSH();self.txn='charging-icon-r8-eud-off-directed'
 def action(self,a,confirmed=False,**kw):
  return launcher.run(a,self.txn,confirmed,ssh=kw.pop('ssh',self.ssh),private=self.root/'output',pins=self.pins,migration=self.migration,**kw)
 def test_01_frozen_worker_audit_and_import_inert(self):
  old=HERE.parents[1]/'charging-ui-audit-20261023/icon-capture-r7-candidate'
  for n in ['worker.py','audit.py','baseline-test-result.json']:self.assertEqual((HERE/n).read_bytes(),(old/n).read_bytes())
  with patch('pathlib.Path.read_bytes',side_effect=AssertionError('import read')),patch('subprocess.run',side_effect=AssertionError('network')):load(HERE/'launcher.py','inert_new')
  compile(launcher.REMOTE,'new-rpc','exec')
  boot,guard,_=launcher.reviewed_identity(self.pins)
  self.assertIn('eud-boot-r2-live-001-adopted',guard);self.assertTrue(boot)
 def test_02_actual_current_identity_semantics_reject_changed_pins(self):
  launcher.adopt_local(HERE,self.pins,self.migration)
  for name,key,value in [('adoption','baseline481_verified',False),('adopt_result','old_guards_preserved',False),('endpoint','postboot_R3_passed',False),('endpoint','observed_new_boot','11111111-2222-4333-8444-555555555555')]:
   original=Path(self.entries[name]['path']).read_bytes();data=json.loads(original);data[key]=value;Path(self.entries[name]['path']).write_text(json.dumps(data))
   self.entries[name]['sha256']=launcher.sha(Path(self.entries[name]['path']).read_bytes());self.pins.write_text(json.dumps(self.entries))
   with self.assertRaises(ValueError):launcher.reviewed_identity(self.pins)
   Path(self.entries[name]['path']).write_bytes(original);self.entries[name]['sha256']=launcher.sha(original);self.pins.write_text(json.dumps(self.entries))
  self.assertFalse(self.ssh.calls)
 def test_03_fixed_300_second_launch_and_unknown_dispatch_no_retry(self):
  self.assertEqual(inspect.signature(launcher.run).parameters['max_seconds'].default,300)
  with self.assertRaises(ValueError):self.action('launch',True,max_seconds=180)
  with self.assertRaises(ValueError):self.action('launch')
  result=self.action('launch',True);self.assertTrue(result['launch_receipt_verified']);self.assertFalse(result['may_prompt_user'])
  r=self.ssh.calls[0];self.assertEqual(r['max_seconds'],300);self.assertIn('/capture-entry.py',r['argv'][1]);self.assertEqual(r['manifest_sha256'],launcher.MANIFEST)
  self.assertEqual(r['identity_expected'],launcher.runtime_expected(self.pins))
  with self.assertRaises(FileExistsError):self.action('launch',True)
  self.assertEqual(len(self.ssh.calls),1)
  def unknown(*args,**kw):raise TimeoutError('transport outcome unknown')
  self.txn='charging-icon-r8-eud-off-unknown'
  with self.assertRaises(TimeoutError):self.action('launch',True,ssh=unknown)
  with self.assertRaises(FileExistsError):self.action('launch',True)
  self.assertTrue((self.root/'output'/self.txn/'launch-request-private.json').exists())
 def test_04_ready_requires_two_fresh_ticks_pid_argv_and_identity(self):
  self.action('launch',True);r=self.ssh.calls[0];good=ready(r)
  self.assertTrue(launcher.ready_check(good,r)['may_prompt_user'])
  for mutate in [lambda d:d.update(identity_unchanged=False),lambda d:d['observations'][1]['status'].update(tick=10),
   lambda d:d['observations'][1]['process'].update(start_ticks=999),lambda d:d['observations'][1]['process'].update(argv=['other']),
   lambda d:d['observations'][1]['status'].update(realtime=1),lambda d:d['observations'][1]['status'].update(remaining_boottime_seconds=129)]:
   d=copy.deepcopy(good);mutate(d);self.assertFalse(launcher.ready_check(d,r)['may_prompt_user'])
  short=copy.deepcopy(good)
  for item in short['observations']:
   item['remote_boottime']+=160;item['remote_realtime']+=160
   item['status']['realtime']+=160;item['status']['t']+=160;item['status']['remaining_boottime_seconds']-=160
  result=launcher.ready_check(short,r);self.assertFalse(result['may_prompt_user'])
  self.assertTrue(result['reasons']);self.assertTrue(all('less than 130 seconds' in reason for reason in result['reasons']))
  self.assertTrue(self.action('status')['may_prompt_user'])
 def test_05_actual_transport_keeps_original_key_ipv6(self):
  call=launcher.transport(self.pins)
  with patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'{}',stderr=b'')) as run:call('read-only-test',check=False)
  argv=run.call_args.args[0]
  for flag in ['-6','HostKeyAlias=169.254.42.1','StrictHostKeyChecking=yes','IdentitiesOnly=yes','BatchMode=yes']:self.assertIn(flag,argv)
  self.assertEqual(argv[-2],'root@fe80::62:bcff:fe28:a101%29');self.assertEqual(run.call_count,1)
 def test_06_sample_adapter_keeps_real_500_and_missing_values(self):
  io=entry.CaptureIO();io.battery=Path('/testBattery')
  telemetry='valid=1 online=1 protection_ok=1 age_ms=1 gauge_current_ua=20000'
  table={'/sys/bus/i2c/devices/0-005c/telemetry':telemetry,
   '/sys/class/power_supply/samurai-usb-input/online':1,'/sys/class/power_supply/mp2650-input/online':1,
   '/testBattery/status':'Discharging','/testBattery/current_now':-31000,'/testBattery/current_avg':{'errno':2,'error':'FileNotFoundError'},
   '/sys/class/power_supply/samurai-usb-input/usb_type':'Unknown [SDP] DCP CDP C',
   '/sys/class/power_supply/samurai-usb-input/current_max':500000,'/sys/class/power_supply/samurai-usb-input/input_current_limit':500000,
   '/sys/class/power_supply/mp2650-input/input_current_limit':500000,'/sys/class/power_supply/mp2650-input/status':'Charging',
   '/sys/class/udc/a600000.usb/state':'configured','/sys/class/udc/a600000.usb/current_speed':'high-speed',
   '/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower':500}
  calls=[]
  def read(path,numeric=False):calls.append(str(path));return table[str(path)]
  with patch.object(worker.RealIO,'read',staticmethod(read)),patch.object(worker.time,'monotonic',side_effect=[20,20.01,20.03]):row=io.sample(10)
  self.assertEqual(row['source']['current_max_ua'],500000);self.assertEqual(row['hardware_input']['input_current_limit_ua'],500000)
  self.assertEqual(row['MaxPower_ma'],500);self.assertEqual(row['battery']['status'],'Discharging');self.assertEqual(row['battery']['current_now_ua'],-31000)
  self.assertEqual(row['battery']['current_avg_ua']['errno'],2);self.assertEqual(row['telemetry']['gauge_current_ua'],20000);self.assertAlmostEqual(row['t_end'],10.03)
  table['/sys/class/power_supply/samurai-usb-input/current_max']={'errno':61,'error':'OSError'}
  with patch.object(worker.RealIO,'read',staticmethod(read)),patch.object(worker.time,'monotonic',side_effect=[21,21.01,21.03]):row=io.sample(10)
  self.assertEqual(row['source']['current_max_ua']['errno'],61);self.assertFalse(any('reg14' in s.lower() for s in calls))
 def test_07_actual_remote_identity_checks_new_guard_kernel_and_notes(self):
  expected=dict(release='k363+',version='#363',rootfs=launcher.sha(b'rootfs'),notes={'samurai_mp2650':launcher.sha(b'note')})
  data=dict(expected_boot='newboot',manifest_sha256=launcher.sha(b'manifest'),identity_expected=expected)
  values={'/proc/sys/kernel/random/boot_id':b'newboot','/guard':b'newboot','/usr/share/samurai-charging/manifest.json':b'manifest',
   '/etc/samurai-rootfs-release':b'rootfs','/sys/module/samurai_mp2650/notes/.note.gnu.build-id':b'note','/sys/module/samurai_mp2650/initstate':b'live'}
  class P:
   def __init__(self,*p):self.name='/'.join(str(x).rstrip('/') for x in p)
   def read_bytes(self):return values[self.name]
   def read_text(self):return self.read_bytes().decode()
  nodes=[n for n in ast.parse(launcher.REMOTE).body if isinstance(n,ast.FunctionDef) and n.name in ['boot_identity','identity','checked_identity']]
  env=dict(data=data,Path=P,guard=P('/guard'),sha=launcher.sha,os=SimpleNamespace(uname=lambda:SimpleNamespace(release='k363+',version='#363')))
  env.update(identity_errors=[],traceback=traceback);exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-rpc-identity','exec'),env);self.assertTrue(env['identity']())
  for name in ['/guard','/etc/samurai-rootfs-release','/sys/module/samurai_mp2650/notes/.note.gnu.build-id']:
   original=values[name];values[name]=b'changed'
   with self.assertRaises(AssertionError):env['identity']()
   values[name]=original
  data['action']='fetch';values['/etc/samurai-rootfs-release']=b'changed'
  self.assertFalse(env['checked_identity']());self.assertEqual(len(env['identity_errors']),1)
  data['action']='status'
  with self.assertRaises(AssertionError):env['checked_identity']()
  data['action']='fetch';values['/guard']=b'wrongboot'
  with self.assertRaises(AssertionError):env['checked_identity']()
 def test_08_fetch_same_worker_only_keeps_original_bytes(self):
  self.action('launch',True);result=self.action('fetch');self.assertTrue(result['cleanup_confirmed']);self.assertFalse(result['may_prompt_user'])
  self.assertEqual((Path(result['retained_directory'])/'capture/capture-private.json').read_bytes(),b'{"retained":"original"}\n')
  self.assertEqual([r['action'] for r in self.ssh.calls],['launch','fetch'])
  self.assertFalse(launcher.cleanup_check(dict(exact_worker_state='alive',worker_terminal=True,monitor_started=True,monitor_errors=[],dbus_returncode=0)))
 def test_09_entry_uses_frozen_main_then_restores_class_and_default_check_local(self):
  original=worker.RealIO;original_cycle=worker.Cycle
  def main(argv):self.assertIs(worker.RealIO,entry.CaptureIO);self.assertIs(worker.Cycle,entry.CaptureCycle);return 7
  with patch.object(worker,'main',side_effect=main):self.assertEqual(entry.main(['x']),7)
  self.assertIs(worker.RealIO,original);self.assertIs(worker.Cycle,original_cycle)
  with patch.object(launcher,'adopt_local',return_value=({},'boot','guard')) as check,patch('subprocess.run',side_effect=AssertionError('network')):launcher.main([])
  self.assertEqual(check.call_count,1)
 def cycle(self):
  c=entry.CaptureCycle()
  for t in range(9):c.feed(self.row(t,not 3<=t<=5))
  self.assertEqual(c.settle_at,8);return c
 def row(self,t,on=True):
  return dict(t_start=t,t_end=t,source_online=int(on),acok_online=int(on),telemetry=dict(valid=1,online=1,protection_ok=1,shadow=0,age_ms=0,error=0,stop_error=0,latched=0,source_inhibit=0,fault=0))
 def test_10_reconnect_25_seconds_is_not_complete(self):
  c=self.cycle()
  for t in range(9,34):phase=c.feed(self.row(t))
  self.assertEqual(phase,'settling');self.assertFalse(c.complete);self.assertEqual(c.settle_at,8)
 def test_11_reconnect_90_seconds_completes(self):
  c=self.cycle()
  for t in range(9,98):self.assertNotEqual(c.feed(self.row(t)),'complete')
  self.assertEqual(c.feed(self.row(98)),'complete');self.assertTrue(c.complete)
 def test_12_off_or_gap_restarts_settling_from_fresh_on_samples(self):
  for event in ['off','gap']:
   c=self.cycle()
   for t in range(9,34):c.feed(self.row(t))
   at=34 if event=='off' else 37
   self.assertEqual(c.feed(self.row(at,event!='off')),'offline_or_transition' if event=='off' else 'sample_gap')
   self.assertIsNone(c.settle_at);self.assertFalse(c.complete)
   for t in range(at+1,at+4):c.feed(self.row(t))
   self.assertEqual(c.settle_at,at+3)
   for t in range(at+4,at+93):self.assertNotEqual(c.feed(self.row(t)),'complete')
   self.assertEqual(c.feed(self.row(at+93)),'complete')
if __name__=='__main__':unittest.main(verbosity=2)
