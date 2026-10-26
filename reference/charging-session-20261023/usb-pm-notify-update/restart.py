"""Retain Image504/carriers: original guarded quiesce and one bootloader restart."""
from pathlib import Path
import argparse,ast,base64,importlib.util,json,os,sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
spec=importlib.util.spec_from_file_location('notify_update',Path(__file__).resolve().parent/'host.py')
update=importlib.util.module_from_spec(spec);spec.loader.exec_module(update)
TX='charging-r7-pm-notify-20261024-01'
REMOTE=update.REMOTE+'/restart'
def build():
 r=update.request();c=json.loads((update.LEAF/'cohort-result.json').read_bytes())
 prefix=update.ROOT/'reference/charging-oem-audit-20261023/normal-restart-candidate'
 source={}
 for name in ['quiesce','restart']:
  text=(prefix/('r7-'+name+'-review.py')).read_text()
  text=update.replace(text,"assert os.uname().version.startswith('#363 ')","assert os.uname().version=="+repr(update.VERSION))
  if name=='quiesce':
   text=update.replace(text,"command(['/usr/sbin/samurai-charging','stop'])","assert json.loads(Path("+repr(update.REMOTE+'/device-stage/result.json')+").read_bytes())['stop_verified'] is True")
   text=update.replace(text,"['samurai-charging','samurai-gnss-assist'","['samurai-gnss-assist'")
  text=text.replace("assert sys.argv[3]", "assert sys.argv[3]",1)
  extra="""
assert hashlib.sha256(Path('/sys/devices/soc0/serial_number').read_bytes()).hexdigest()==meta['serial_sha256']
assert hashlib.sha256(Path('/sys/firmware/devicetree/base/compatible').read_bytes()).hexdigest()==meta['compatible_sha256']
assert Path(meta['adoption_guard']).read_text().strip()==meta['boot_id']
stage=Path(meta['stage_result']);raw=stage.read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['stage_result_sha256']
sr=json.loads(raw);assert sr['staged'] and sr['terminal'] and sr['stop_verified'] and sr['disk_state']=='all_new_fsynced' and not sr['primary_error'] and not sr['recovery_error']
assert Path('/sys/class/power_supply/samurai-gauge-protection/health').read_text().strip()=='Good'
"""
  point="assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'"
  text=update.replace(text,point,point+'\n'+extra)
  # Same original body, including all camera/audio/DSP/display/NV checks and EUD exit.
  ast.parse(text);source[name]=text.encode()
 meta=dict(schema='samurai-r7-restart-review-v1',transaction_id=TX,boot_id=r['identity']['boot_id'],kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',kernel_version=update.VERSION,
  rootfs_release_sha256=r['identity']['rootfs_sha256'],disk_pair={
  '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko':c['target_usb_sha256'],
  '/usr/share/samurai-charging/manifest.json':c['target_manifest_sha256']},old_loaded_usb_note_sha256=c['source_module_note_sha256'],
  serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],adoption_guard=r['adoption']['guard_path'],stage_result=update.REMOTE+'/device-stage/result.json')
 return source,meta
def prepare():
 source,meta=build();out=update.OUT/'restart-local';out.mkdir(mode=0o700)
 for name,raw in source.items():update.create(out/(name+'.py'),raw)
 update.save(out/'meta-template.json',meta)
 return dict(prepared=True,carrier_writes=0,normal_bootloader_reboot_only=True)
def quiesce():
 source,meta=build();rows=sorted(update.OUT.glob('raw-*/device-stage/result.json'));update.need(len(rows)==1,'one actual completed stage')
 sr=rows[0].read_bytes();result=json.loads(sr);update.need(result['staged'] and result['terminal'] and result['disk_state']=='all_new_fsynced','stage incomplete')
 meta['stage_result_sha256']=update.sha(sr)
 packet=dict(root=REMOTE,meta=meta,source={k:base64.b64encode(v).decode() for k,v in source.items()},hashes={k:update.sha(v) for k,v in source.items()})
 code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,runpy,sys
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==PACKET['meta']['boot_id']
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077);root.mkdir(mode=0o700)
for name,value in PACKET['source'].items():
 raw=base64.b64decode(value,validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET['hashes'][name]
 with (root/(name+'.py')).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
with (root/'guard.json').open('x') as f:json.dump(PACKET['meta'],f);f.flush();os.fsync(f.fileno())
sys.argv=['quiesce','--guard',str(root/'guard.json'),'--commit-quiesce']
runpy.run_path(str(root/'quiesce.py'),run_name='__main__')
print(json.dumps(dict(quiesced=True,state=json.loads((Path('/var/lib/samurai')/PACKET['meta']['transaction_id']/'state-private.json').read_bytes()),summary=json.loads((Path('/var/lib/samurai')/PACKET['meta']['transaction_id']/'summary.json').read_bytes()))))
'''
 return update.call('quiesce',code,False)
def restart():
 q=json.loads((update.OUT/'quiesce/reply.json').read_bytes());update.need(q['quiesced'] and q['state']['terminal'] and q['state']['exit_code']==0,'original quiesce not complete')
 code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import runpy,sys
root=Path(REMOTE)
sys.argv=['restart','--guard',str(root/'guard.json'),'--inspect']
try:runpy.run_path(str(root/'restart.py'),run_name='__main__')
except SystemExit as e:assert e.code==0
sys.argv=['restart','--guard',str(root/'guard.json'),'--commit-restart2-bootloader']
runpy.run_path(str(root/'restart.py'),run_name='__main__')
'''
 # The original transport saves/waits the actual SSH child; a disconnect is
 # expected only after dispatch. Never repeat: inspect fastboot/current boot.
 return update.call('restart-dispatch',code,False)
def restart2():
 # First inspect refused before claiming a reboot: EUD is already disabled.
 # Retain that failure; use the exact previously exercised EUD-off syscall tail.
 original=build()[0]['restart'].decode()
 current=update.ROOT/'reference/charging-session-20261023/irq-native-usb-pm-activation-device-candidate'
 common=(current/'common.py').read_text();tree=ast.parse(common)
 eud=next(ast.get_source_segment(common,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='eud_off_check')
 tail=(current/'eud-restart.py').read_text().split('# eud_off_check already passed in the common read-only guard.\n',1)[1]
 marker="device=Path('/sys/bus/platform/devices/88e0000.serial');"
 update.need(original.count(marker)==1,'original EUD-on tail')
 source=(original.split(marker,1)[0]+eud+'\neud_off_check()\n'+"meta['token']="+repr(update.request()['lease_token'])+'\n'+tail).encode();ast.parse(source)
 update.create(update.OUT/'restart-local/restart-eud-off-r2.py',source)
 packet=dict(root=REMOTE,source=base64.b64encode(source).decode(),sha256=update.sha(source))
 code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,runpy,sys
root=Path(PACKET['root']);assert not Path('/run/charging-r7-pm-notify-20261024-01-reboot-phase-private.json').exists()
raw=base64.b64decode(PACKET['source'],validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET['sha256']
with (root/'restart-eud-off-r2.py').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
sys.argv=['restart','--guard',str(root/'guard.json'),'--inspect']
try:runpy.run_path(str(root/'restart-eud-off-r2.py'),run_name='__main__')
except SystemExit as e:assert e.code==0
sys.argv=['restart','--guard',str(root/'guard.json'),'--commit-restart2-bootloader']
runpy.run_path(str(root/'restart-eud-off-r2.py'),run_name='__main__')
'''
 return update.call('restart-dispatch-r2',code,False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','quiesce','restart','restart2']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
