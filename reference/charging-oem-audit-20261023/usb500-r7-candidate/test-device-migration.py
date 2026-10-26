"""Directed R7-only boundary tests. Does not run the frozen51-case suite."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;D=HERE/'device-candidate'
spec=importlib.util.spec_from_file_location('r7_worker',D/'worker.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
P=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
actual=(P/'r7-handoff/snapshot-private.json').read_bytes();sample=json.loads(actual)
cases=[]
def ok(label,value=True):assert value,label;cases.append(label)
def reject(label,fn):
 try:fn()
 except RuntimeError:ok(label);return
 raise AssertionError(label)
def row(ma=100,full=False):
 r=copy.deepcopy(sample);r.pop('dmesg',None);r.pop('result',None)
 r['limits'].update(native_ua=ma*1000,source_budget_ua=ma*1000,input_ua=ma*1000)
 r['sample']['budget_ua']=ma*1000
 r['registers']['00']=(r['registers']['00']&~0x7f)|(ma//50)
 r['registers']['0f']=(r['registers']['0f']&~0x7f)|(ma//50)
 r['source']={'online':'1','usb_type':'Unknown [SDP] DCP CDP C','current_max':str(ma*1000),'input_current_limit':str(ma*1000)}
 r['udc']='configured'
 if full:
  r['sample'].update(logical_full=1,hold_requested=1,full_holding=1,full_cause=1,desired_enable=0,session_seconds=0)
  r['registers']['08']&=~0x18
 return r

ok('actual R7 handoff SDP100 receiver',w.accepted(row(),100)=='managed')
ok('R7 exact Full receiver',w.accepted(row(500,True),500)=='full_holding')
bad=row(500);bad['limits']['source_budget_ua']=100000
reject('effective source field cannot alias raw native',lambda:w.accepted(bad,500))
bad=row();bad['source'].update(usb_type='Unknown SDP DCP [CDP]',current_max='1500000');bad['limits']['source_budget_ua']=1500000;bad['sample']['budget_ua']=1500000
reject('CDP1.5A/native100 cannot qualify SDP trial',lambda:w.accepted(bad,100))
bad=row();bad['sample'].update(flags=bad['sample']['flags']|0x4000,gauge_charge_stop=1,error=-11)
reject('TCA is not healthy Full receiver',lambda:w.accepted(bad,100))

# Actual new observe() reads distinct kernel properties; all file edges fake.
mapping={
 '/sys/class/power_supply/samurai-usb-input/input_current_limit':'100000',
 '/sys/class/power_supply/samurai-usb-input/current_max':'1500000',
 '/sys/class/power_supply/mp2650-input/input_current_limit':'100000',
 '/sys/class/power_supply/mp2650-input/constant_charge_current':'250000'}
class FakePath:
 def __init__(self,*parts):self.value='/'.join(str(p).rstrip('/') for p in parts)
 def __str__(self):return self.value
 def __truediv__(self,part):return FakePath(self.value,part)
 def read_text(self):return mapping[self.value]
 def read_bytes(self):assert self.value.startswith('/sys/module/');return self.value.encode()
 def exists(self):assert self.value=='/run/openrc/started/samurai-charging';return True
manager={'live':SimpleNamespace(state=lambda:copy.deepcopy(sample['state']),PSY=FakePath('/sys/class/power_supply')),'sample':lambda:copy.deepcopy(sample['sample'])}
with patch.object(w.r6,'Path',FakePath):observed=w.r6.Device.observe(object(),manager)
ok('actual observe distinguishes raw100 and effective1500',observed['limits']['native_ua']==100000 and observed['limits']['source_budget_ua']==1500000)

ready=[{'ifname':'usb0','addr_info':[{'local':'fe80::62:bcff:fe28:a101','prefixlen':64,'scope':'link'}]}]
tentative=copy.deepcopy(ready);tentative[0]['addr_info'][0]['flags']=['tentative']
wrong=copy.deepcopy(ready);wrong[0]['addr_info'][0]['local']='fe80::1'
ok('only original completed IPv6 peer accepted',w.ipv6_ready(ready) and not w.ipv6_ready(tentative) and not w.ipv6_ready(wrong))
class IfPath:
 def __init__(self,*parts):assert parts==(w.GADGET,'functions/ncm.usb0/ifname')
 def read_text(self):return 'usb0\n'
class Net:
 def __init__(self,rows):self.clock=0;self.rows=rows;self.calls=[]
 def now(self):return self.clock
 def pause(self,seconds):self.clock+=seconds
 def net_command(self,args,deadline):
  self.calls.append(args)
  if args[:3]==['ip','link','set']:return ''
  return json.dumps(self.rows.pop(0) if len(self.rows)>1 else self.rows[0])
net=Net([tentative,ready])
with patch.object(w,'Path',IfPath):w.Diagnostic.network(net,45)
ok('actual IPv6 network helper waits DAD and never IPv4/add',net.clock>.1 and net.calls[0]==['ip','link','set','usb0','up'] and all('-4' not in a and 'add' not in a for a in net.calls))
net=Net([wrong])
with patch.object(w,'Path',IfPath):reject('absent original IPv6 fails bounded without fallback',lambda:w.Diagnostic.network(net,45))
ok('missing peer only3seconds and no address injection',2.9<=net.clock<=3.01 and all('add' not in a for a in net.calls))

# Prove unchanged control and quarantine methods without rerunning51 cases.
old=HERE.parents[1]/'charging-session-20261023/usb500-diagnostic/device-candidate/worker.py'
def functions(text):
 tree=ast.parse(text)
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
of,nf=functions(old.read_text()),functions((D/'worker.py').read_text())
for name in ['configure','stable','transaction','gadget_state','write','net_command','check_window','event','finish']:
 assert of[name]==nf[name],name
ok('45s finally100 unknown-child lease/journal control AST unchanged')

class IO:
 def __init__(self,mode):
  self.mode=mode;self.clock=0;self.touched=False;self.uncertain=False;self.started=True;self.restoring=False
  self.state={'binding':w.BINDING,'power_ma':100};self.mutations=[]
 def now(self):return self.clock
 def pause(self,seconds):self.clock+=seconds
 def begin(self,c):pass
 def preflight(self):return row()
 def environment(self):return {}
 def event(self,*args,**kwargs):pass
 def gadget_state(self):return dict(self.state)
 def write(self,field,value,stage,deadline):
  self.touched=True;self.mutations.append((field,value,stage))
  if self.mode=='unknown' and stage=='500:power':self.uncertain=True;raise w.r6.MutationUncertain('fake pending child')
  self.state['binding' if field=='UDC' else 'power_ma']=value.strip() if field=='UDC' else int(value)
 def network(self,deadline):pass
 def snapshot(self):return row(100 if self.mode=='rejected' and self.state['power_ma']==500 else self.state['power_ma'])
 def finish(self,r):self.result=copy.deepcopy(r)
 def close(self):pass
for mode in ['accepted','rejected','unknown']:
 io=IO(mode);result=w.transaction({'host_trigger_nonce':'a'*48},io)
 if mode=='unknown':
  ok('unknown child remains quarantined no100 race',not result['terminal'] and result['mutating_state_unknown'] and not any(x[2].startswith('100:') for x in io.mutations))
 else:
  ok(mode+'500 always one finally100',result['terminal'] and result['restore100_verified'] and result['native500_accepted']==(mode=='accepted') and sum(x[2]=='500:power' for x in io.mutations)==sum(x[2]=='100:power' for x in io.mutations)==1 and io.state=={'binding':w.BINDING,'power_ma':100})

result={'schema':'usb500-r7-migration-v1','passed':True,'cases':len(cases),'sequences':cases,
 'tested_files':{name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in ['worker.py','r7-base.py','health.py']},
 'test_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'actual_r7_handoff_sha256':hashlib.sha256(actual).hexdigest(),
 'frozen51_suite_rerun':False,'device_access':False,'usb_access':False,'sdk_access':False,'trial_executed':False}
(D/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(cases),'full51_rerun':False,'device_access':False},indent=2))
