"""Current504 three-file cold stage; original device safety and transport retained."""
from pathlib import Path
import argparse,ast,base64,importlib.util,inspect,json,os,secrets,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('profile_update_original',HERE.parent/'usb-pm-notify-update/host.py')
u=importlib.util.module_from_spec(s);s.loader.exec_module(u)
PREVIOUS=u.OUT;u.OUT=u.BASE/'protection-profile-update-live-20261024-03'
u.TX='irq-native-usb-pm-stage-protocol-20261024-03';u.REMOTE='/root/charging-management-20261023/'+u.TX
u.LEAF=HERE
def assigned(source,name,value):
 tree=ast.parse(source);found=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name]
 assert len(found)==1,name;n=found[0];lines=source.splitlines(True);lines[n.lineno-1:n.end_lineno]=[name+'='+repr(value)+'\n'];return ''.join(lines)
def function(source,name,new):
 tree=ast.parse(source);n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);lines=source.splitlines(True);lines[n.lineno-1:n.end_lineno]=[new+'\n'];return ''.join(lines)
def bind():
 assert not u.OUT.exists(),'intent exists; inspect original'
 c=json.loads((HERE/'cohort-r2-result.json').read_bytes());assert c['passed'] and c['source_manifest_sha256']=='94a659ad1fd30c4014ac335a6802ef3d279bdf908408d4b99e13867132b46b82'
 pointer=(u.BASE/'boot-adoption-private.json').read_bytes();assert pointer==(PREVIOUS/'adoption-pointer.json').read_bytes();current=json.loads(pointer)
 assert current['PM_suspend_resume_verified'] and current['charging_manifest_sha256']==c['source_manifest_sha256'] and current['boot_id']=='eb9e051a-da47-4d98-8c9c-cfc7f4e8664a'
 os.umask(0o077);u.OUT.mkdir(mode=0o700);u.create(u.OUT/'previous-pointer.json',pointer)
 observed=u.call('cache-read',('EXPECTED='+repr(current['boot_id'])+'\n').encode()+br'''
from pathlib import Path
import hashlib,json
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED
raw=Path('/sys/devices/platform/samurai-gauge-protection/mac_evidence').read_bytes()
first=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split())
assert first['schema']=='1' and (first['attempted'],first['terminal']) in [('0','0'),('1','1')]
print(json.dumps(dict(sha256=hashlib.sha256(raw).hexdigest(),first=first)))
''')
 before=(PREVIOUS/'stage-worker.py').read_text();source=before
 protection='/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko'
 service='/usr/sbin/samurai-charging';manifest='/usr/share/samurai-charging/manifest.json'
 values=dict(USB=protection,ORDER=[protection,service,manifest],OLD=c['source_manifest_sha256'],NEW=c['target_manifest_sha256'],USB_OLD=c['source_protection_sha256'],USB_NEW=c['target_protection_sha256'],
  NOTES={'samurai-usb-input':'f3c8d708a7122549a8733b5c171a2c2895e63eccaa76e31e5dfdbd9ca2ff46ae','samurai-gauge-protection':c['source_protection_note_sha256'],'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'},
  MAC_CACHE_SHA=observed['sha256'],COHORT=u.sha((HERE/'cohort-r2-result.json').read_bytes()),PAYLOAD=c['forward']['sha256'],OLD_FILES=c['source_files'],NEW_FILES=c['target_files'])
 for key,value in values.items():source=assigned(source,key,value)
 source=u.replace(source,'len(raw)==27182','len(raw)=='+str(c['forward']['bytes']))
 source=u.replace(source,"need(len(members)==2,'exact two files')","need(len(members)==3,'exact protection/service/manifest files')")
 modes={protection:0o600,service:0o755,manifest:0o600}
 source=source.replace("OLD_FILES=",'MODES='+repr(modes)+'\nOLD_FILES=',1)
 source=u.replace(source,"m.mode==0o600 and m.uid==m.gid==0","m.mode==MODES[target] and m.uid==m.gid==0")
 # Preserve executable mode through the same exclusive temp/fsync/rename and
 # rollback path; backups themselves remain private non-executable data.
 source=u.replace(source,'path = Path(path)\n    temporary',"path = Path(path)\n    target_mode = MODES[str(path)]\n    temporary")
 source=u.replace(source,"need(mode == 0o600 and sha(old) == expected_old","need(mode == target_mode and sha(old) == expected_old")
 source=u.replace(source,"os.O_EXCL | os.O_NOFOLLOW, 0o600)","os.O_EXCL | os.O_NOFOLLOW, target_mode)")
 source=u.replace(source,'ops.fchmod(fd, 0o600)','ops.fchmod(fd, target_mode)')
 source=u.replace(source,"actual == raw and mode == 0o600","actual == raw and mode == target_mode")
 source=u.replace(source,"'mode': '0600', 'file_and_directory_fsynced'","'mode': oct(target_mode), 'file_and_directory_fsynced'")
 source=u.replace(source,"need(mode==0o600 and sha(raw)==OLD_FILES[name]","need(mode==MODES[name] and sha(raw)==OLD_FILES[name]")
 source=u.replace(source,"need(mode==0o600,'exact original mode')","need(mode==MODES[name],'exact original target mode')")
 source=u.replace(source,"need(mode==0o600 and sha(current) in","need(mode==MODES[name] and sha(current) in")
 source=u.replace(source,"mode==0o600 and digest==OLD_FILES[name]","mode==MODES[name] and digest==OLD_FILES[name]")
 source=u.replace(source,"mode==0o600 and digest==NEW_FILES[name]","mode==MODES[name] and digest==NEW_FILES[name]")
 source=u.replace(source,"result['identity'] = device.identity(request)\n        old_raw, mode", "result['identity'] = device.identity(request)\n        for name in ORDER:\n            actual, target_mode = device.read_owned(name)\n            need(target_mode == MODES[name] and sha(actual) == OLD_FILES[name], 'all three actual source modes/hashes')\n        old_raw, mode")
 source=u.replace(source,"need(sha(self.read_owned(SERVICE)[0]) == manager['_r8_code_sha256'], 'cannot verify with stale in-memory manager')\n        return manager['verify']()",
  "digest = sha(self.read_owned(SERVICE)[0])\n        need(digest in (SERVICE_SHA, NEW_FILES[SERVICE]), 'known old/new manager for read-only verification')\n        return self.manager(digest)['verify']()")
 source=u.replace(source,"return self.manager_for_stop()['live'].registers()",
  "digest = sha(self.read_owned(SERVICE)[0])\n        need(digest in (SERVICE_SHA, NEW_FILES[SERVICE]), 'known old/new manager for read-only registers')\n        return self.manager(digest)['live'].registers()")
 delta='''def manifest_delta(old,new):
    expected=copy.deepcopy(old)
    need(old['release']==RELEASE and old['modules']['samurai-gauge-protection']=={'target':USB,'sha256':USB_OLD},'current actual protection7848')
    expected['adapter_revision']='protection-observed-2719-profile-01'
    expected['modules']['samurai-gauge-protection']['sha256']=USB_NEW
    expected['installed_files'][USB]=USB_NEW
    expected['installed_files'][SERVICE]=NEW_FILES[SERVICE]
    need(new==expected and old['installed_files'][SERVICE]==SERVICE_SHA,'only protection/service opt-in/cohort change')
    need(old['modules']['samurai-usb-input']['sha256']=='ebfcb45d436f0f08dcaf4e400ea18b18cf3bd208863de33444e76c20faab4624' and old['modules']['samurai-mp2650']['sha256']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd','retain actual USB PM fix and charger')
    need(old['default_input_cap_ua']==900000 and old['default_charge_cap_ua']==250000 and old['source_budget_enforced'] is True,'unchanged charging policy')'''
 source=function(source,'manifest_delta',delta);ast.parse(source)
 def bodies(text):
  tree=ast.parse(text);return {n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 old_funcs,new_funcs=bodies(before),bodies(source)
 changed=['unpack','manifest_delta','atomic_replace','Device','SnapshotBase','stage','preflight']
 assert set(old_funcs)==set(new_funcs) and all(new_funcs[k]==v for k,v in old_funcs.items() if k not in changed)
 u.create(u.OUT/'stage-worker.py',source.encode());worker=u.load(u.OUT/'stage-worker.py','profile_stage_local')
 a=json.loads((PREVIOUS/'request-private.json').read_bytes());identity={**a['identity'],'boot_id':current['boot_id']}
 tx=Path(current['guard_path']).parent.name.removesuffix('-adopted')
 payload=(u.BASE/'protection-observed-2719-cohort-private-02/forward-three-files.tar.gz').read_bytes();assert u.sha(payload)==c['forward']['sha256']
 req=dict(schema='samurai-irq-native-usb-pm-stage-request-v1',transaction_id=u.TX,cohort_delivery_sha256=worker.COHORT,payload_sha256=c['forward']['sha256'],payload_base64=base64.b64encode(payload).decode(),
  worker_sha256=u.sha(source.encode()),lease_token=secrets.token_hex(24),identity=identity,
  adoption=dict(transaction_id=tx,guard_path=current['guard_path'],guard_sha256=u.sha((current['boot_id']+'\n').encode())))
 worker.unpack(req);worker.manifest_delta(json.loads((u.BASE/'protection-observed-2719-cohort-private-02/manifest-old.json').read_bytes()),json.loads((u.BASE/'protection-observed-2719-cohort-private-02/manifest-new.json').read_bytes()))
 u.save(u.OUT/'request-private.json',req);u.save(u.OUT/'derivation.json',dict(passed=True,base_stage_sha256=u.sha(before.encode()),derived_stage_sha256=u.sha(source.encode()),
  original_safety_stopped_rollback_and_manager_mutation_gates_exact=True,changed_functions=changed,
  readonly_verify_and_registers_freshly_import_exact_old_or_new_service_only=True,
  expanded_ORDER_three_known_files=True,worker_loaded_or_query_started=False))
 return dict(bound=True,three_files=True,query_started=False)
def launch():
 body=inspect.getsource(u.launch)
 body=u.replace(body,"'rollback-two-files.tar.gz':(BASE/'usb-input-pm-notify-cohort-private-02/rollback-two-files.tar.gz')","'rollback-three-files.tar.gz':(BASE/'protection-observed-2719-cohort-private-02/rollback-three-files.tar.gz')")
 namespace=dict(u.__dict__);exec(compile(body,'<same-supervised-stage-launch>','exec'),namespace);return namespace['launch']()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['bind','preflight','launch','fetch']);a=p.parse_args()
 f=bind if a.action=='bind' else launch if a.action=='launch' else getattr(u,a.action)
 print(json.dumps(f(),indent=2))
