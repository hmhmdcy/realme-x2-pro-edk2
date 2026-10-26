"""Affected actual Python functions only; finite fake OS, no phone/transport."""
from pathlib import Path
import ast,base64,contextlib,copy,hashlib,importlib.util,io,json,struct,sys,tempfile,types
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=(HERE/'device.py').read_text();env={'__name__':'offline_actual_functions'}
exec(compile(source,'actual-device-source','exec'),env)
spec=importlib.util.spec_from_file_location('postboot_payload_tests',HERE/'payload.py')
payload=importlib.util.module_from_spec(spec);spec.loader.exec_module(payload)
assert payload.check_local()['local_checks_passed']
wrapper_path=PRIVATE/'kernel481/formal-expected-private.json'
wrapper=json.loads(wrapper_path.read_bytes())
health_path=PRIVATE/'kernel481/final-health-r2-private.json'
health=json.loads(health_path.read_bytes())
groups=[]
def rejected(fn):
 try:fn()
 except (AssertionError,KeyError,ValueError):return
 raise AssertionError('expected rejection')
def fact(digest):return dict(sha256=digest,regular=True,symlink=False,uid=0,mode=0o644)

guard={'schema':'samurai-eud-boot-activation-v1','transaction_id':'eud-boot-fixture-new',
 'token':'4e'*16,'boot_id':'11111111-2222-3333-4444-555555555555',
 'kernel_release':'7.3.0-rc6-rmx1931-samurai-k363+','kernel_version':'#363 fixture-version',
 'rootfs_release_sha256':'a'*64,'soc_serial_sha256':'b'*64,
 'compatible_sha256':hashlib.sha256(b'realme,samurai\0qcom,sm8150\0').hexdigest(),**payload.FIXED}
identity={'boot_id':'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
 'uname':dict(machine='aarch64',release=guard['kernel_release'],version=guard['kernel_version']),
 'taint':'0','rootfs':fact(guard['rootfs_release_sha256']),
 'serial_sha256':guard['soc_serial_sha256'],'compatible_b64':base64.b64encode(b'realme,samurai\0qcom,sm8150\0').decode()}
assert env['check_identity'](identity,guard)['new_boot']
for key,value in [('boot_id',guard['boot_id']),('serial_sha256','0'*64)]:
 r=copy.deepcopy(identity);r[key]=value;rejected(lambda:env['check_identity'](r,guard))
groups.append('actual new-boot identity rejects old UUID and wrong board serial')

sample=health['health']['samples'][0]['telemetry']
def charging(kind='SDP',budget=100000,native=100000,ilim=100000,full=False):
 t={**sample,'budget_ua':budget}
 if full:t.update(logical_full=1,desired_enable=0,full_holding=1,hold_requested=1,full_cause=2)
 text=' '.join(k+'='+str(v) for k,v in t.items())
 return {'source':dict(online='1',usb_type='['+kind+']',current_max=str(budget),input_current_limit=str(native)),
 'charger':dict(online='1',health='Good',charge_behaviour='[auto]',input_current_limit=str(ilim),constant_charge_current='250000',constant_charge_voltage='8725000'),
 'telemetry_before':text,'telemetry_after':text,'config_max_power_ma':'100',
 'protection_state':'id=0x2719 error=0 safety=0 pf=0 operation=0x300 manufacturing=0x18 pf_enabled=0'}
assert env['check_charging'](charging())['ready']
assert env['check_charging'](charging('SDP',500000,500000,500000))['budget_ua']==500000
assert env['check_charging'](charging('CDP',1500000,100000,900000))['budget_ua']==1500000
assert env['check_charging'](charging(full=True))['state']==['healthy_full_charge_only_hold']*2
rejected(lambda:env['check_charging'](charging('SDP',100000,100000,150000)))
rejected(lambda:env['check_charging'](charging('SDP',500000,100000,100000)))
groups.append('actual charging checks real SDP/CDP budgets, inherited caps and precise logical Full')
r=charging();r['source']['current_max']={'error':'OSError','errno':61};assert env['check_charging'](r)==dict(state='waiting_source',source_type='SDP',ready=False)
r=charging();r['source']['usb_type']={'error':'OSError','errno':61};assert env['check_charging'](r)['ready'] is False
r=charging();r['telemetry_after']=r['telemetry_after'].replace('cycle_timeout=0','cycle_timeout=1');rejected(lambda:env['check_charging'](r))
groups.append('source ENODATA stays waiting without fabricated100; old timeout rejected')

expected=wrapper['expected']
r={'camera_files':{p:fact(d) for p,d in expected['installed_files'].items()},
 'camera_modules':{n:{**fact(v['sha256']),'loaded_note_matches_disk':True,'loaded_note_sha256':v['note']} for n,v in expected['modules'].items()},
 'camera_module_live':{n:'live' for n in expected['modules']},'sensor_note':env['SENSOR468_NOTE'],'sensor_live':'live',
 'package_db':'\n\n'.join('P:'+p+'\nV:'+v for p,v in expected['packages'].items()),
 'm2m':json.dumps(health['camera_after']['status']),'core':json.dumps(health['camera_after']['core']),
 'pm':health['camera_after']['pm'],'user_services':{n:[dict(pid=100+i,start_ticks=str(200+i),uid=10000)] for i,n in enumerate(env['SERVICES'])}}
assert json.loads(r['m2m'])['owner_refs']==57 and env['check_camera'](r,expected)['four_PM_and_m2m_idle']
r['user_services']['phosh'][0]['uid']=0;rejected(lambda:env['check_camera'](r,expected))
groups.append('actual camera481 checker accepts retained owner_refs57 and collects new service identities')

e={'dt_com_nodes':[dict(status='disabled\0')],'cmdline':'console=tty0',
 'chosen_bootargs':'console=tty0\0','bound_com_devices':[],'tty_devices':[],
 'proc_consoles':'tty0 -WU (EC p a) 4:1','active_console':'tty0','chosen_stdout_path':{'error':'FileNotFoundError'}}
assert env['check_producers']({'eud':e})['CSR_MMIO_read'] is False
e['cmdline']='earlycon';rejected(lambda:env['check_producers']({'eud':e}))
groups.append('actual producer checker rejects even implicit earlycon and never queries CSR')

def ring(text):
 data=text.encode();size=0x14000-32
 fields=[0x474f4c45,0x10000,size,len(data),0,0,0,0]
 raw=struct.pack('<8I',*fields)+data+bytes(size-len(data))
 return dict(raw_b64=base64.b64encode(raw).decode(),header_before=fields,header_after=fields,header_stable=True)
marker='[SAMURAI-EUD-OFF] attempted=1 write=1 arm=01010101 before=01010101 after=00000000 status=Success\n'
decoded=env['decode_ring'](ring(marker));assert decoded['ready'] and decoded['parsed'][0]['after']==0
assert decoded['callback_success_independently_proven'] is False
assert not env['decode_ring'](ring('unrelated private firmware line\n'))['ready']
assert not env['decode_ring'](ring(marker.replace('after=00000000','after=01000000')))['ready']
assert not env['decode_ring'](ring(marker+marker))['ready']
groups.append('actual ring decoder only publishes whitelist; missing/failure/ambiguous markers never pass')

# Actual proven capture function, with only OS/Path/mmap boundaries fake.
capture=ring(marker);image=base64.b64decode(capture['raw_b64']);calls=[]
class P:
 def __init__(self,x):assert x=='/proc/iomem'
 def read_text(self):return '9ffe3000-9fff6fff : reserved\n'
class Mapping:
 def __enter__(self):return image
 def __exit__(self,*args):return False
fake_mmap=types.SimpleNamespace(MAP_SHARED=1,PROT_READ=1,mmap=lambda fd,length,**kw:(calls.append((fd,length,kw)) or Mapping()))
saved={n:env[n] for n in ['os','Path']};old_mmap=sys.modules.get('mmap')
env['Path']=P
env['os']=types.SimpleNamespace(sysconf=lambda n:4096,O_RDONLY=0,O_SYNC=0x1000,O_CLOEXEC=0x80000,
 open=lambda p,flags:(calls.append((p,flags)) or 777),close=lambda fd:calls.append(('close',fd)))
try:
 sys.modules['mmap']=fake_mmap
 with contextlib.redirect_stderr(io.StringIO()):captured=env['read_ring']()
 assert captured['raw_b64']==capture['raw_b64'] and captured['hardware_writes']==0
 assert calls[0]==('/dev/mem',0x81000) and calls[1][2]==dict(flags=1,prot=1,offset=0x9ffe3000)
finally:
 env.update(saved)
 if old_mmap is None:del sys.modules['mmap']
 else:sys.modules['mmap']=old_mmap
groups.append('actual reserved RAM capture uses only established O_RDONLY/PROT_READ range')

with tempfile.TemporaryDirectory(prefix='eud-postboot-fixture-') as d:
 root=Path(d);graw=json.dumps(guard).encode();(root/'guard-private.json').write_bytes(graw)
 ctx=dict(schema='samurai-eud-fastboot-context-v1',transaction_id=guard['transaction_id'],token=guard['token'],
  old_boot_id=guard['boot_id'],guard_sha256=hashlib.sha256(graw).hexdigest(),
  files={'guard':dict(path='guard-private.json',sha256=hashlib.sha256(graw).hexdigest())})
 cp=root/'host-context-private.json';cp.write_text(json.dumps(ctx))
 request=payload.make_request(cp,wrapper_path,'fixture-new-endpoint',True,True)
 assert request['guard']['boot_id']==guard['boot_id'] and request['context_sha256']==sha(cp)
 emitted=payload.make_payload(request);ast.parse(emitted)
 ctx['old_boot_id']='old-wrong';cp.write_text(json.dumps(ctx));rejected(lambda:payload.make_request(cp,wrapper_path,'fixture-new-endpoint',True,True))
groups.append('actual payload builder binds context exact raw guard, old boot, wrapper and explicit endpoint')

request={'schema':'samurai-eud-postboot-readonly-v1','new_endpoint':'fixture-endpoint','original_key_transport_verified':True,
 'guard':guard,'context_sha256':'c'*64,'guard_sha256':'d'*64}
old_collect=env['collect']
def fail_collect(request,raw):raw['partial_original']='kept';raise OSError(5,'finite read boundary')
env['collect']=fail_collect
try:
 out=io.StringIO()
 with contextlib.redirect_stdout(out):code=env['main'](['--execute','--window-confirmed','--new-endpoint','fixture-endpoint'],request)
 report=json.loads(out.getvalue());assert code==1 and report['raw']['partial_original']=='kept'
finally:env['collect']=old_collect
groups.append('actual main preserves partial originals on ordinary collection failure without recovery')

with tempfile.TemporaryDirectory(prefix='eud-postboot-receiver-fixture-') as d:
 raw_report={'raw':{'secret_identity':'must_not_publish','ring':ring(marker)},
             'result':{'passed':True,'checks':{'EUD_ring_receipt':env['decode_ring'](ring(marker))},'errors':{}}}
 stdout=json.dumps(raw_report).encode()
 public=payload.save_response(Path(d)/'captured-private',stdout,b'header-private',0,b'fixture-source')
 assert public['passed'] and 'secret_identity' not in json.dumps(public) and 'raw_b64' not in json.dumps(public)
 assert (Path(d)/'captured-private/stdout-private.json').read_bytes()==stdout
 assert (Path(d)/'captured-private/eud-ring-private.bin').read_bytes()==base64.b64decode(ring(marker)['raw_b64'])
 failed=payload.save_response(Path(d)/'partial-private',b'{partial',b'original-error',255,b'fixture-source')
 assert not failed['passed'] and failed['decode_error_class']=='JSONDecodeError'
 assert (Path(d)/'partial-private/stdout-private.json').read_bytes()==b'{partial'
groups.append('actual private receiver preserves partial/full originals and publishes only whitelist')

result=dict(passed=True,groups=groups,group_count=len(groups),actual_device_functions=True,hardware_OS_IO_fake=True,
 fixture_basis={str(wrapper_path):sha(wrapper_path),str(health_path):sha(health_path)},
 tested_files={n:sha(HERE/n) for n in ['device.py','device-body.py','payload.py','prepare.py','test-boundaries.py','contract.json']},
 old_suites_rerun=False,workers_collected=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,groups=len(groups),device_access=False)))
