"""Specialize the existing rollback transport for the current two-file cohort."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-oem-audit-20261023/rollback-connected-candidate'
BINDER=HERE.parent/'irq-native-usb-pm-rollback-host-candidate';WORKER=HERE.parent/'irq-native-usb-pm-cold-rollback-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def replace(text,before,after,count=1):
 assert text.count(before)==count,(before,text.count(before));return text.replace(before,after)
def emit(name,raw):
 assert not (HERE/'delivery.json').exists(),'frozen output'
 path=HERE/name
 if isinstance(raw,str):raw=raw.encode()
 if path.exists():assert path.read_bytes()==raw,name
 else:path.write_bytes(raw)
def functions(text):
 return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def main():
 assert sys.argv[1:]==['--prepare']
 assert sha((OLD/'delivery.json').read_bytes())=='d94d774233aebff0e6fef8cb9d0a8a3e1e3f35d18fda43a70d17981b13012e60'
 assert sha((BINDER/'delivery.json').read_bytes())=='38bd3b781485b53f23a5f1771a7da129b68faec7166d1acecf11d33539113d0f'
 original={name:(OLD/name).read_text() for name in ['host.py','remote.py','supervisor.py']}
 expected={'host.py':'da2b6ee9163eace29192124bd4c421d2e7cdc92a498f9a1981b91bc50228dc18',
  'remote.py':'becb1dbe8f2293d60a6d3fc18933ae2eb0ace99e1faca2c0d9554a497312c8fc',
  'supervisor.py':'c61df9a42d77e9af83a8fa50fd4ab2a9a1860cc642477f9774136ae65d4d94e9'}
 for name in expected:assert sha((OLD/name).read_bytes())==expected[name]
 host=original['host.py'];old_funcs=functions(host)
 host=replace(host,old_funcs['source_check'],(HERE/'source-check.py.inc').read_text().strip())
 host=host.replace('usb-irq-protection-rollback-','irq-native-usb-pm-rollback-')
 host=replace(host,"charging-management-20261023/usb-irq-protection-rollback'","charging-management-20261023/irq-native-usb-pm-rollback'")
 host=host.replace('samurai-rollback-connected-binding-v1','samurai-irq-native-usb-pm-rollback-connected-binding-v1')
 host=host.replace('str(Path(stage_directory).resolve())','str(local(stage_directory).resolve())').replace('str(Path(stage_fetch_directory).resolve())','str(local(stage_fetch_directory).resolve())').replace('str(Path(probe_directory).resolve())','str(local(probe_directory).resolve())').replace('str(Path(context).resolve())','str(local(context).resolve())')
 before="and request['source_stage']==reviewed['saved']['source_stage'] and request['activation']==reviewed['saved']['activation']"
 after="and request['source_stage']==reviewed['saved']['source_stage'] and request['activation']==reviewed['saved']['activation']\n             and request['source_stage_observations']==reviewed['saved']['source_stage_observations']\n             and request['current_cache']==reviewed['current']['current_cache']"
 host=replace(host,before,after)
 host=replace(host,"module=load_module(HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py','rollback_final_fixed_identities')", "module=load_module(source_check()[0]['worker']['path'],'rollback_final_fixed_identities')")
 host=replace(host,"module.expected_profile(request)[1]","module.expected_profile(request)['notes']")
 host=replace(host,"argv=[key.SSH,'-6','-T',*key.OPTIONS","argv=[key.SSH,'-C','-6','-T',*key.OPTIONS")
 host=replace(host,"def main():",(HERE/'probe-owner.py.inc').read_text().strip()+'\n\n\ndef main():')
 host=replace(host,"('check-local','bind','launch','status','fetch')","('check-local','probe','bind','launch','status','fetch')")
 host=replace(host,"parser.add_argument('--context');parser.add_argument('--window-confirmed'","parser.add_argument('--context');parser.add_argument('--output');parser.add_argument('--window-confirmed'")
 host=replace(host,"    elif args.action=='bind':", "    elif args.action=='probe':\n        need(args.window_confirmed,'current coordinated window required')\n        value=probe(args.profile,args.stage_directory,args.stage_fetch_directory,args.output,args.context)\n    elif args.action=='bind':")
 remote=original['remote.py'].replace('usb-irq-protection-rollback-','irq-native-usb-pm-rollback-').replace('samurai-usb-irq-protection-rollback-request-v1','samurai-irq-native-usb-pm-cold-rollback-request-v1').replace('f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142','6818939b88a51ccd9d0455438c73ac3ad51c26332acdf8d1ea31096bdfc80c47')
 supervisor=replace(original['supervisor.py'],'samurai-usb-irq-protection-rollback-request-v1','samurai-irq-native-usb-pm-cold-rollback-request-v1')
 for name,text in [('host.py',host),('remote.py',remote),('supervisor.py',supervisor)]:compile(text,name,'exec');emit(name,text)
 exact=['local','need','create','save','load_module','process_identity','process_status','ssh_owner','start_job','terminal_job','review_launch_transport']
 new_funcs=functions(host)
 assert all(old_funcs[name]==new_funcs[name] for name in exact)
 assert functions(supervisor)['supervise']==functions(original['supervisor.py'])['supervise'].replace('samurai-usb-irq-protection-rollback-request-v1','samurai-irq-native-usb-pm-cold-rollback-request-v1')
 entries=dict(binder=BINDER/'bind.py',binder_delivery=BINDER/'delivery.json',worker=WORKER/'restore-worker.py',worker_delivery=WORKER/'delivery.json',
  legacy_delivery=OLD/'delivery.json',key_transport=REF/'kernel184/host.py',profile=REF/'charging-oem-audit-20261023/irq-postboot-compressed-profile/profile.py',
  profile_delivery=REF/'charging-oem-audit-20261023/irq-postboot-compressed-profile/delivery.json',host=HERE/'host.py',remote=HERE/'remote.py',supervisor=HERE/'supervisor.py')
 pins={key:dict(path=str(path.resolve()),sha256=sha(path.read_bytes()),bytes=path.stat().st_size) for key,path in entries.items()}
 emit('source-pins.json',json.dumps(pins,indent=2)+'\n')
 emit('source-reuse.json',json.dumps(dict(passed=True,exact_host_functions=exact,supervisor_change='request schema only',
  remote_changes='transaction prefix, request schema and exact current worker hash only',
  old_host_sha256=expected['host.py'],old_remote_sha256=expected['remote.py'],old_supervisor_sha256=expected['supervisor.py'],
  original_matrix_reused_not_rerun=True,device_accessed=False),indent=2)+'\n')
 print(json.dumps(dict(prepared=True,device_accessed=False,runtime_request_created=False)))
if __name__=='__main__':main()
