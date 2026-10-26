"""Reuse existing restore qualification and hardware tails for the current cohort."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=HERE.parent/'usb-irq-protection-rollback-restart-candidate'
CURRENT=HERE.parent/'irq-native-usb-pm-rollback-connected-candidate'
DEVICE=HERE.parent/'irq-native-usb-pm-activation-device-candidate'
BINDER=HERE.parent/'irq-native-usb-pm-rollback-host-candidate'
WORKER=HERE.parent/'irq-native-usb-pm-cold-rollback-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def emit(name,text):
 assert not (HERE/'delivery.json').exists(),'frozen source'
 raw=text.encode() if isinstance(text,str) else text;path=HERE/name
 path.write_bytes(raw)
def change(text,before,after,count=1):
 assert text.count(before)==count,(before,text.count(before));return text.replace(before,after)
def functions(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def assignments(text,values):
 tree=ast.parse(text);parts=[]
 for node in tree.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
   parts.append((node.lineno-1,node.end_lineno,node.targets[0].id))
 lines=text.splitlines(keepends=True)
 assert {key for _,_,key in parts}==set(values)
 for start,end,key in reversed(parts):lines[start:end]=[key+'='+repr(values[key])+'\n']
 return ''.join(lines)
def main():
 assert sys.argv[1:]==['--prepare']
 assert sha((OLD/'delivery.json').read_bytes())=='b16b7f8d31adb2ae1acab0d1a376edf19fe64f3a65e9c74f9a1f75d9164445ce'
 assert sha((CURRENT/'delivery.json').read_bytes())=='8902891c9f6059a694d2732679a6df6a0e3eeb4737dcf8e5f01b6b6fed46076d'
 worker=(WORKER/'restore-worker.py').read_text();constants={}
 for node in ast.parse(worker).body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
   try:constants[node.targets[0].id]=ast.literal_eval(node.value)
   except (ValueError,TypeError):pass
 oldproof=(OLD/'proof.py').read_text();proof=assignments(oldproof,dict(BOOT=constants['BOOT'],WORKER=sha(worker.encode()),SUPERVISOR=sha((CURRENT/'supervisor.py').read_bytes()),TX_PATTERN=r'irq-native-usb-pm-rollback-activate-[a-z0-9-]{8,48}'))
 proof=change(proof,"r'usb-irq-protection-rollback-[a-z0-9-]{8,48}'","r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}'")
 proof=change(proof,"worker.expected_profile(request)[1]","worker.expected_profile(request)['notes']")
 body=functions((HERE/'proof-body.py.inc').read_text())
 for name in ['post_probe_request','make_guard']:proof=change(proof,functions(proof)[name],body[name])
 before="    current = report['current']; identity = current['identity']"
 proof=change(proof,before,before+"\n    need(report['cache_before']==current['current_cache']==report['cache_after']==after['current_cache']==request['current_cache'],\n         'same held post-restore cache bracket')")
 proof=change(proof,"        auth = sources.load('auth_host'); auth.source_check()","        auth = sources.load('rollback_binder').auth_module()")
 before="    need(not value.get('automatic_replay_or_rollback')"
 proof=change(proof,before,"    for name in ['before-private.json','stopped-private.json','after-private.json']:\n        observation=json.loads(raws[name]);worker.validate_cache(observation['current_cache'])\n        need(observation['current_cache']==request['current_cache'],'original cache across restore')\n"+before)
 compile(proof,'proof.py','exec');emit('proof.py',proof)
 common=(OLD/'common.py').read_text();oldcommon=common
 package=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01/rollback-manifest.json')
 if sys.platform!='win32':package=Path('/mnt/e/'+str(package).replace('\\','/')[3:])
 manifest=json.loads(package.read_bytes());assert sha(package.read_bytes())==constants['OLD_FILES'][constants['MANIFEST']]
 common=assignments(common,dict(BOOT=constants['BOOT'],OLD=constants['OLD_FILES'][constants['MANIFEST']],OLD_NOTES=constants['OLD_NOTES'],OLD_FILES=constants['OLD_FILES'],EXPECTED_MANIFEST=manifest,PROOF_SHA=sha(proof.encode())))
 extra="\n_MAC_FD=None\n_CACHE_EXPECTED=None\n_ROLLBACK_MODULE=None\n_RESTORED_AFTER=None\nVERSION504="+repr(constants['VERSION504'])+'\n'
 common=common[:common.index('\ndef secure_file')]+extra+common[common.index('\ndef secure_file'):]
 runtime=functions((HERE/'runtime-body.py.inc').read_text())
 for name in ['observe_staged','staged_health']:common=change(common,functions(common)[name],runtime[name])
 guard=(OLD/'device-guard.inc').read_text()
 guard=guard.replace('samurai-usb-irq-protection-rollback-restart-v1','samurai-irq-native-usb-pm-rollback-restart-v1').replace('usb-irq-protection-rollback-activate-','irq-native-usb-pm-rollback-activate-')
 guard=change(guard,'def rollback_material(meta):','def rollback_material(meta):\n global _ROLLBACK_MODULE,_RESTORED_AFTER,_CACHE_EXPECTED')
 guard=change(guard," expected_boot,expected_notes=module.expected_profile(request)\n need(meta['current_boot_sha256']==expected_boot and meta['resident_notes']==expected_notes,'explicit rollback profile constants')",
  " expected=module.expected_profile(request)\n need(meta['current_boot_sha256']==expected['boot'] and meta['current_logdump_sha256']==expected['logdump'] and\n  meta['resident_notes']==expected['notes'] and meta['current_cache']==request['current_cache'],'explicit current rollback profile')\n _ROLLBACK_MODULE=module;_RESTORED_AFTER=json.loads(raw['after']);_CACHE_EXPECTED=request['current_cache']")
 guard=change(guard,"'unchanged_logdump_sha256','boot_bytes'","'unchanged_boot_sha256','current_logdump_sha256','current_cache','boot_bytes'")
 guard=guard.replace('rollback_boot_sha256','rollback_logdump_sha256')
 guard=change(guard,"meta['kernel_version']==VERSION and meta['partitions']==['boot']","meta['kernel_version'] in (VERSION,VERSION504) and meta['partitions']==['logdump']")
 guard=change(guard,"meta['rollback_logdump_sha256']==BOOT and meta['unchanged_logdump_sha256']==LOGDUMP","meta['rollback_logdump_sha256']==LOGDUMP and meta['unchanged_boot_sha256']==BOOT and meta['current_boot_sha256']==BOOT")
 guard=change(guard,"os.uname().version==VERSION,'only exact current Image502'","os.uname().version==meta['kernel_version'],'exact actual current profile kernel'")
 guard=change(guard,"block_sha('/dev/disk/by-partlabel/logdump',67108864)==LOGDUMP","block_sha('/dev/disk/by-partlabel/logdump',67108864)==meta['current_logdump_sha256']")
 guard=change(guard," OLD_NOTES=dict(worker.expected_profile(request)[1])"," OLD_NOTES=dict(worker.expected_profile(request)['notes'])\n verify_current_cache(meta['current_cache'])")
 guard=change(guard," data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))"," data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME));verify_current_cache(meta['current_cache'])")
 original_functions=functions(common)
 for name,new in functions(guard).items():common=change(common,original_functions[name],new)
 cache=functions((DEVICE/'common.py').read_text())['verify_consumed_cache'].replace('verify_consumed_cache','verify_current_cache').replace("sha(raw)==MAC_CACHE_SHA==expected['sha256']","sha(raw)==expected['sha256']")
 cache=change(cache,"need(first.get('attempted')==first.get('terminal')=='1','no new MAC capture')","need(first.get('schema')=='1' and (first.get('attempted'),first.get('terminal')) in [('0','0'),('1','1')],'no in-progress or new MAC capture')\n return dict(expected)")
 common+='\n\n'+cache+'\n';compile(common,'common.py','exec');emit('common.py',common);emit('device-guard.inc',guard)
 for name in ['eud-quiesce.py','eud-restart.py']:
  text=(OLD/name).read_text();assert text.count(oldcommon)==1,name
  emitted=text.replace(oldcommon,common);compile(emitted,name,'exec');emit(name,emitted)
 sources=(OLD/'sources.py').read_text().replace('samurai-irq-rollback-restart-sources-v1','samurai-irq-native-usb-pm-rollback-restart-device-sources-v1')
 emit('sources.py',sources)
 entries=dict(rollback_host=CURRENT/'host.py',rollback_host_delivery=CURRENT/'delivery.json',rollback_worker=WORKER/'restore-worker.py',rollback_worker_delivery=WORKER/'delivery.json',
  rollback_supervisor=CURRENT/'supervisor.py',rollback_binder=BINDER/'bind.py',current_probe=BINDER/'current-probe.py',
  old_delivery=OLD/'delivery.json',old_common=OLD/'common.py',old_proof=OLD/'proof.py',old_quiesce=OLD/'eud-quiesce.py',old_restart=OLD/'eud-restart.py',
  current_forward_common=DEVICE/'common.py',camera_wrapper=Path('E:/edk2-samurai-out/kernel481/formal-expected-private.json'),key_transport=REF/'kernel184/host.py')
 def local(path):return Path('/mnt/e/'+str(path).replace('\\','/')[3:]) if sys.platform!='win32' and str(path).startswith('E:') else path
 baseline={key:dict(path=str(local(path).resolve()),sha256=sha(local(path).read_bytes()),bytes=local(path).stat().st_size) for key,path in entries.items()}
 names=['sources.py','proof.py','common.py','device-guard.inc','eud-quiesce.py','eud-restart.py','proof-body.py.inc','runtime-body.py.inc','prepare.py']
 emit('source-pins.json',json.dumps(dict(schema='samurai-irq-native-usb-pm-rollback-restart-device-sources-v1',baseline=baseline,
  local={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in names}),indent=2)+'\n')
 exact=[name for name,text in functions(oldcommon).items() if functions(common).get(name)==text]
 emit('source-reuse.json',json.dumps(dict(passed=True,unchanged_common_functions=exact,hardware_tail_and_prefix_byte_exact=True,
  readonly_cache_change='current exact request instance; 0/0 or 1/1, no query',stop_safety='actual current worker safe_stopped/idle/retained, no AUTO',
  target='logdump ace2 only, bootedd read-only',device_accessed=False),indent=2)+'\n')
 print(json.dumps(dict(prepared=True,device_accessed=False,runtime_request_created=False,unchanged_common_functions=len(exact))))
if __name__=='__main__':main()
