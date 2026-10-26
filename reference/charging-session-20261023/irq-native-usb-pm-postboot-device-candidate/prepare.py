"""Specialize the frozen IRQ read-only collector; no device or runtime request."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-oem-audit-20261023/irq-cohort-postboot-readonly'
PROBE=HERE.parent/'irq-native-usb-pm-rollback-host-candidate/current-probe.py'
WORKER=HERE.parent/'irq-native-usb-pm-cold-rollback-candidate'
PM=Path('E:/edk2-samurai-out/charging-management-20261023/native-usb-pm-current-readonly-01-private/executed-device-source.py')
PACKAGE=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def local(path):return Path('/mnt/e/'+str(path).replace('\\','/')[3:]) if sys.platform!='win32' and str(path).startswith('E:') else path
def emit(name,text):
 assert not (HERE/'delivery.json').exists(),'frozen source';raw=text.encode() if isinstance(text,str) else text
 (HERE/name).write_bytes(raw)
def funcs(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def methods(text,name):
 cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name==name)
 return {n.name:ast.get_source_segment(text,n) for n in cls.body if isinstance(n,ast.FunctionDef)}
def method_lines(text,name,method):
 cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name==name)
 node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==method)
 return ''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
def main():
 assert sys.argv[1:]==['--prepare']
 assert sha((OLD/'delivery.json').read_bytes())=='b2c1d2de692b2d302450b0debbfdd50221b84790523829dc57b5c96ba271689b'
 original=(OLD/'device.py').read_text();assert sha(original.encode())=='78337b7801b21e120f7814a2f8857e52dc1056ef80364821a6507d5faf2a444d'
 probe=PROBE.read_text();assert sha(probe.encode())=='98a19ad35095172d7e0de5bcb8a9da33cb33d83feded35fadd55d0c5c6ad6403'
 pm=local(PM).read_text();assert sha(pm.encode())=='f5e91e657355cc46d0e3ba3e4559c18a6fae0846f0d59b3b9c25d42d2bfdd833'
 constants={}
 for node in ast.parse((WORKER/'restore-worker.py').read_text()).body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
   try:constants[node.targets[0].id]=ast.literal_eval(node.value)
   except (ValueError,TypeError):pass
 profiles={}
 for name,filename,version,image,logdump,notes,link in [
  ('forward_504','manifest.json',constants['VERSION504'],'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4',constants['LOGDUMP504'],constants['NEW_NOTES'],True),
  ('restored_502','rollback-manifest.json',constants['VERSION502'],'085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',constants['LOGDUMP502'],constants['OLD_NOTES'],False)]:
  raw=(local(PACKAGE)/filename).read_bytes()
  expected=constants['NEW_FILES' if link else 'OLD_FILES'][constants['MANIFEST']];assert sha(raw)==expected
  profiles[name]=dict(version=version,image=image,logdump=logdump,manifest_sha256=sha(raw),manifest=json.loads(raw),
   notes={key.replace('-','_'):value for key,value in notes.items()},system_pm_link=link)
 emit('profiles.json',json.dumps(profiles,indent=2)+'\n')
 original_funcs=funcs(original);device=original
 check=original_funcs['check_identity'].replace("r['uname']['version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'","r['uname']['version']==g['target_kernel_version']==EXPECTED_VERSION")
 check=check.replace(" assert r['boot_id']!=g['boot_id'],'still old boot'"," assert r['boot_id']!=g['boot_id'],'still old boot'\n assert r['boot_id']==g['new_boot_id'],'exact fresh-probed new boot'")
 check=check.replace("'same_board_release_rootfs_new_Image502':True","'same_board_release_rootfs_target_kernel':True")
 device=device.replace(original_funcs['check_identity'],check)
 install=original_funcs['check_install'].replace("m['adapter_revision']=='usb-irq-protection-observer-01'","m['adapter_revision']==EXPECTED_REVISION")
 device=device.replace(original_funcs['check_install'],install)
 device=device.replace(original_funcs['collect'],original_funcs['collect'].replace('def collect(','def collect_base(',1))
 audit=original_funcs['audit'].replace('def audit(r,request):','def audit(r,request):\n validate_request(request)')
 audit=audit.replace("('identity_after',lambda:check_identity(r['identity_after'],request['guard']))]", "('protection_cache_instance',lambda:check_cache(r)),('native_system_pm_link',lambda:check_pm_topology(r,request)),\n  ('identity_after',lambda:check_identity(r['identity_after'],request['guard']))]")
 assert audit!=original_funcs['audit'] and "'native_system_pm_link'" in audit
 device=device.replace(original_funcs['audit'],audit)
 body=funcs((HERE/'current-body.py.inc').read_text())
 for name in ['check_partitions','main']:device=device.replace(original_funcs[name],body.pop(name))
 helpers=funcs(probe);evidence=methods(probe,'ProbeIdentity');file_methods=methods(probe,'Probe')
 cache='\n\n'+helpers['need']+'\n\n'+helpers['validate_cache']+'\n\nINSTANCE='+repr(constants['INSTANCE'])+'\n'
 cache+='\nclass CacheEvidence:\n'+method_lines(probe,'ProbeIdentity','cache_evidence')
 cache+='\nclass CacheFile:\n    def __init__(self):\n        self.mac_fd=None;self.baseline=None\n'
 for name in ['open_cache','close']:cache+=method_lines(probe,'Probe',name)
 cache+='\nclass CacheReader(CacheEvidence,CacheFile):\n    pass\n'
 pm_funcs=funcs(pm);cache+='\n'+pm_funcs['links']+'\n\n'+pm_funcs['snapshot'].replace('def snapshot(','def pm_snapshot(',1)+'\n'
 definitions='\nPROFILES='+repr(profiles)+'\nEXPECTED_VERSION=EXPECTED_LOGDUMP=EXPECTED_IMAGE=EXPECTED_REVISION=None\n'
 definitions+=cache+'\n\n'+'\n\n'.join(body.values())+'\n'
 marker="\nif __name__=='__main__':raise SystemExit(main(request=globals().get('POSTBOOT_REQUEST')))"
 assert device.count(marker)==1;device=device.replace(marker,definitions+marker)
 compile(device,'device.py','exec');emit('device.py',device)
 old_identity=REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/identity-probe.py'
 host_delivery=old_identity.parent/'delivery.json'
 assert sha(host_delivery.read_bytes())=='8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'
 assert json.loads(host_delivery.read_bytes())['files']['identity-probe.py']['sha256']==sha(old_identity.read_bytes())
 identity=old_identity.read_text()
 identity=identity.replace("r['uname']['version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'","r['uname']['version']==g['target_kernel_version']==EXPECTED_VERSION")
 identity=identity.replace("'same_board_release_rootfs_new_Image502':True","'same_board_release_rootfs_target_kernel':True")
 identity=identity.replace("def main(request=None):","EXPECTED_VERSION=None\nPROFILES="+repr({name:row['version'] for name,row in profiles.items()})+"\n\ndef main(request=None):\n global EXPECTED_VERSION")
 identity=identity.replace("assert request['schema']=='samurai-irq-postboot-identity-probe-v1'","assert request['schema']=='samurai-irq-native-usb-pm-postboot-identity-probe-v1'\n assert request['profile'] in PROFILES\n EXPECTED_VERSION=PROFILES[request['profile']]\n assert request['guard']['target_kernel_version']==EXPECTED_VERSION")
 compile(identity,'identity-probe.py','exec');emit('identity-probe.py',identity)
 exact=[name for name,text in original_funcs.items() if funcs(device).get(name)==text]
 emit('source-reuse.json',json.dumps(dict(passed=True,unchanged_original_functions=exact,
  collector_body_change='only rename collect to collect_base; outer holds readonly cache and adds PM topology',
  cache_helpers_byte_exact=['need','validate_cache','cache_evidence','open_cache','close'],
  pm_links_byte_exact=True,pm_snapshot_change='function name only',old_matrices_rerun=False,device_accessed=False),indent=2)+'\n')
 entries=dict(original_device=OLD/'device.py',original_delivery=OLD/'delivery.json',cache_probe=PROBE,cache_probe_delivery=PROBE.parent/'delivery.json',
  worker=WORKER/'restore-worker.py',worker_delivery=WORKER/'delivery.json',pm_inventory=local(PM),
  forward_manifest=local(PACKAGE)/'manifest.json',restored_manifest=local(PACKAGE)/'rollback-manifest.json',
  image504_delivery=REF/'charging-oem-audit-20261023/dwc-image504-budget-fence-candidate/delivery.json',
  old_identity_probe=old_identity,old_identity_host_delivery=host_delivery)
 pins={name:dict(path=str(path.resolve()),sha256=sha(path.read_bytes()),bytes=path.stat().st_size) for name,path in entries.items()}
 emit('source-pins.json',json.dumps(pins,indent=2)+'\n')
 print(json.dumps(dict(prepared=True,profiles=list(profiles),unchanged_functions=len(exact),device_accessed=False)))
if __name__=='__main__':main()
