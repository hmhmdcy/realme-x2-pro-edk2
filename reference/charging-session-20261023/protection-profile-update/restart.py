"""Module-only cold activation: reuse the just-tested EUD-off quiesce/restart."""
from pathlib import Path
import argparse,ast,base64,importlib.util,json,sys
sys.dont_write_bytecode=True
s=importlib.util.spec_from_file_location('protection_update',Path(__file__).resolve().parent/'host.py');adapter=importlib.util.module_from_spec(s);s.loader.exec_module(adapter);u=adapter.u
TX='charging-r7-protection-profile-20261024-03';REMOTE=u.REMOTE+'/restart'
def build():
 r=u.request();c=json.loads((adapter.HERE/'cohort-r2-result.json').read_bytes());old=adapter.PREVIOUS/'restart-local';source={}
 for name,file in [('quiesce','quiesce.py'),('restart','restart-eud-off-r2.py')]:
  text=(old/file).read_text()
  if name=='quiesce':text=u.replace(text,repr('/root/charging-management-20261023/irq-native-usb-pm-stage-notify-20261024-01/device-stage/result.json'),repr(u.REMOTE+'/device-stage/result.json'))
  else:
   prior=json.loads((adapter.PREVIOUS/'request-private.json').read_bytes())['lease_token']
   text=u.replace(text,"meta['token']="+repr(prior),"meta['token']="+repr(r['lease_token']))
  marker="assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'"
  extra="""
for path,digest in meta['changed_files'].items():
 p=Path(path);assert not p.is_symlink() and p.stat().st_uid==0 and not p.stat().st_mode&0o022
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
assert hashlib.sha256(Path('/sys/module/samurai_gauge_protection/notes/.note.gnu.build-id').read_bytes()).hexdigest()==meta['source_protection_note']
"""
  text=u.replace(text,marker,marker+'\n'+extra);ast.parse(text);source[name]=text.encode()
 previous=json.loads((u.OUT/'previous-pointer.json').read_bytes())
 meta=dict(schema='samurai-r7-restart-review-v1',transaction_id=TX,boot_id=r['identity']['boot_id'],kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',kernel_version=u.VERSION,
  rootfs_release_sha256=r['identity']['rootfs_sha256'],disk_pair={
  '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko':c['retained_usb_sha256'],
  '/usr/share/samurai-charging/manifest.json':c['target_manifest_sha256']},old_loaded_usb_note_sha256='f3c8d708a7122549a8733b5c171a2c2895e63eccaa76e31e5dfdbd9ca2ff46ae',
  changed_files=c['target_files'],source_protection_note=c['source_protection_note_sha256'],
  serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],adoption_guard=previous['guard_path'],stage_result=u.REMOTE+'/device-stage/result.json')
 return source,meta
def prepare():
 source,meta=build();out=u.OUT/'restart-local';out.mkdir(mode=0o700)
 for name,raw in source.items():u.create(out/(name+'.py'),raw)
 u.save(out/'meta-template.json',meta);return dict(prepared=True,carrier_writes=0)
def quiesce():
 source,meta=build();rows=list(u.OUT.glob('raw-*/device-stage/result.json'));assert len(rows)==1
 raw=rows[0].read_bytes();result=json.loads(raw);assert result['staged'] and result['terminal'] and result['disk_state']=='all_new_fsynced' and not result['primary_error'] and not result['recovery_error']
 terminal=json.loads((rows[0].parent.parent/'worker-terminal-private.json').read_bytes());assert terminal['terminal'] and terminal['returncode']==0
 meta['stage_result_sha256']=u.sha(raw)
 packet=dict(root=REMOTE,meta=meta,source={k:base64.b64encode(v).decode() for k,v in source.items()},hashes={k:u.sha(v) for k,v in source.items()})
 code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,runpy,sys
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==PACKET['meta']['boot_id']
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077);root.mkdir(mode=0o700)
for name,value in PACKET['source'].items():
 raw=base64.b64decode(value,validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET['hashes'][name]
 with (root/(name+'.py')).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
with (root/'guard.json').open('x') as f:json.dump(PACKET['meta'],f);f.flush();os.fsync(f.fileno())
sys.argv=['quiesce','--guard',str(root/'guard.json'),'--commit-quiesce'];runpy.run_path(str(root/'quiesce.py'),run_name='__main__')
o=Path('/var/lib/samurai')/PACKET['meta']['transaction_id']
print(json.dumps(dict(quiesced=True,state=json.loads((o/'state-private.json').read_bytes()),summary=json.loads((o/'summary.json').read_bytes()))))
'''
 return u.call('quiesce',code,False)
def restart():
 q=json.loads((u.OUT/'quiesce/reply.json').read_bytes());assert q['quiesced'] and q['state']['terminal'] and q['state']['exit_code']==0
 code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import runpy,sys
root=Path(REMOTE)
sys.argv=['restart','--guard',str(root/'guard.json'),'--inspect']
try:runpy.run_path(str(root/'restart.py'),run_name='__main__')
except SystemExit as e:assert e.code==0
sys.argv=['restart','--guard',str(root/'guard.json'),'--commit-restart2-bootloader'];runpy.run_path(str(root/'restart.py'),run_name='__main__')
'''
 return u.call('restart-dispatch',code,False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','quiesce','restart']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
