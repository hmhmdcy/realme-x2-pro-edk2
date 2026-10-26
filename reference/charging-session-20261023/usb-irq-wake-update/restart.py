"""Reuse the actual prior EUD-off cold transition, with this two-file cohort."""
from pathlib import Path
import argparse,ast,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('irq_wake_restart_adapter',HERE/'host.py');u=adapter.u
m=load('irq_wake_prior_restart_owner',HERE.parent/'protection-profile-update/restart.py')
m.adapter=adapter;m.u=u;m.TX='charging-r7-usb-irq-wake-20261024-01';m.REMOTE=u.REMOTE+'/restart'
def build():
 request=u.request();c=json.loads((HERE/'cohort-result.json').read_bytes());source={}
 previous_request=json.loads((adapter.PREVIOUS/'request-private.json').read_bytes())
 for name in ['quiesce','restart']:
  text=(adapter.PREVIOUS/'restart-local'/(name+'.py')).read_text()
  if name=='quiesce':text=u.replace(text,repr('/root/charging-management-20261023/irq-native-usb-pm-stage-protocol-20261024-03/device-stage/result.json'),repr(u.REMOTE+'/device-stage/result.json'))
  else:text=u.replace(text,"meta['token']="+repr(previous_request['lease_token']),"meta['token']="+repr(request['lease_token']))
  ast.parse(text);source[name]=text.encode()
 meta=dict(schema='samurai-r7-restart-review-v1',transaction_id=m.TX,boot_id=request['identity']['boot_id'],kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',kernel_version=u.VERSION,
  rootfs_release_sha256=request['identity']['rootfs_sha256'],disk_pair={
  '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko':c['target_usb_sha256'],
  '/usr/share/samurai-charging/manifest.json':c['target_manifest_sha256']},old_loaded_usb_note_sha256=c['source_usb_note_sha256'],
  changed_files=c['target_files'],source_protection_note=c['retained_protection_note_sha256'],
  serial_sha256=request['identity']['serial_sha256'],compatible_sha256=request['identity']['compatible_sha256'],adoption_guard=request['adoption']['guard_path'],stage_result=u.REMOTE+'/device-stage/result.json')
 return source,meta
m.build=build
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','quiesce','restart']);a=p.parse_args();print(json.dumps(getattr(m,a.action)(),indent=2))
