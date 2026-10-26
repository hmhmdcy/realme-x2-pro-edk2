"""Compose the current device checks with original owner and logdump operator."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=HERE.parent/'usb-irq-protection-rollback-restart-candidate'
DEVICE=HERE.parent/'irq-native-usb-pm-rollback-restart-device-candidate'
C5=HERE.parent/'irq-native-usb-pm-activation-host-candidate'
OP=HERE.parent/'irq-native-usb-pm-activation-device-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def emit(name,text):
 assert not (HERE/'delivery.json').exists(),'frozen source'
 raw=text.encode() if isinstance(text,str) else text;path=HERE/name
 path.write_bytes(raw)
def change(text,before,after,count=1):
 assert text.count(before)==count,(before,text.count(before));return text.replace(before,after)
def functions(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def main():
 assert sys.argv[1:]==['--prepare']
 assert sha((DEVICE/'delivery.json').read_bytes())=='22cf5980a3372aa047a9a90f32f5106089fb4afefe95462457914eeb35aabf94'
 assert sha((OLD/'delivery.json').read_bytes())=='b16b7f8d31adb2ae1acab0d1a376edf19fe64f3a65e9c74f9a1f75d9164445ce'
 assert sha((C5/'controller.py').read_bytes())=='6e6b7e45101f63ecfcf8e9c72cafb56e4daaf9dfbbb7ecfc3f416d122aa9af23'
 assert sha((C5/'remote.py').read_bytes())=='602f2e89058fb1d17ec74ea9131615fc61b59a37d821c4494c36cb2c6984e806'
 assert sha((OP/'fastboot-operator.py').read_bytes())=='3793fd189d8a8db186733d8de974abcbc64f66fc126544ae67b780c107bc123f'
 for name in ['common.py','proof.py','eud-quiesce.py','eud-restart.py']:emit(name,(DEVICE/name).read_bytes())
 controller=(OLD/'controller.py').read_text()
 controller=controller.replace('usb-irq-protection-rollback-activation','irq-native-usb-pm-rollback-activation').replace('samurai-irq-rollback-restart-host-binding-v1','samurai-irq-native-usb-pm-rollback-restart-host-binding-v1').replace('samurai-usb-irq-protection-rollback-fastboot-context-v1','samurai-irq-native-usb-pm-rollback-fastboot-context-v1')
 controller=change(controller,'def main():',(HERE/'host-extra.py.inc').read_text().strip()+'\n\n\ndef main():')
 controller=change(controller,"['check-local','bind','prepare'","['check-local','probe','bind','prepare'")
 controller=change(controller,"parser.add_argument('--post-restore-probe-directory');parser.add_argument('--job')","parser.add_argument('--post-restore-probe-directory');parser.add_argument('--job');parser.add_argument('--output')")
 controller=change(controller,"    if args.action=='bind':", "    if args.action=='probe':\n        sources.need(args.execute and args.window_confirmed,'explicit readonly probe/current window')\n        value=probe(args.rollback_directory,args.rollback_fetch_directory,args.output)\n    elif args.action=='bind':")
 controller=change(controller,"else:value=owner().run(args.action,args.transaction,args.execute,args.window_confirmed)","else:value=run(args.action,args.transaction,args.execute,args.window_confirmed)")
 operator=(OLD/'fastboot-operator.py').read_text().replace('samurai-usb-irq-protection-rollback-fastboot-context-v1','samurai-irq-native-usb-pm-rollback-fastboot-context-v1')
 operator=change(operator,'frozen_source_inputs=module.source_inputs','frozen_local_inputs=module.local_inputs')
 operator=change(operator,'sources.source_check();return frozen_source_inputs()',"sources.source_check();result=frozen_local_inputs()\n            module.IMAGES={'original':module.IMAGES['original']}\n            result['images']={'original':result['images']['original']}\n            return result")
 operator=change(operator,'module.source_inputs=inputs;module.pinned_tools=pinned_tools','module.local_inputs=inputs;module.pinned_tools=pinned_tools')
 # Only the owner-level eager pruning is replaced; inputs() performs the real
 # materialization and exact original-only pruning on every actual use.
 operator=change(operator,"        module.IMAGES={'original':module.IMAGES['original']}\n        module.PAIR_ACTIONS", "        # IMAGES is initialized by the original current local_inputs.\n        module.PAIR_ACTIONS")
 operator=change(operator,'owner().source_inputs()','owner().local_inputs()')
 remote=(OLD/'remote.py').read_text();original_preflight=functions(remote)['preflight'];new_preflight=functions((C5/'remote.py').read_text())['preflight']
 remote=change(remote,original_preflight,new_preflight).replace('usb-irq-protection-rollback-activation-owner','irq-native-usb-pm-rollback-activation-owner').replace('usb-irq-protection-rollback-activate-','irq-native-usb-pm-rollback-activate-')
 for name,text in [('controller.py',controller),('fastboot-operator.py',operator),('remote.py',remote)]:compile(text,name,'exec');emit(name,text)
 emit('supervisor.py',(OLD/'supervisor.py').read_bytes())
 sources=(DEVICE/'sources.py').read_text().replace('samurai-irq-native-usb-pm-rollback-restart-device-sources-v1','samurai-irq-native-usb-pm-rollback-restart-host-sources-v1')
 emit('sources.py',sources)
 contract=json.loads((DEVICE/'prepare-contract.json').read_bytes());contract['host_wiring_complete']=True;contract['actual_runtime_action_performed']=False
 emit('prepare-contract.json',json.dumps(contract,indent=2)+'\n')
 inherited=json.loads((DEVICE/'source-pins.json').read_bytes())['baseline'];baseline=dict(inherited)
 paths=dict(device_delivery=DEVICE/'delivery.json',activation_controller=C5/'controller.py',activation_remote=C5/'remote.py',
  activation_controller_delivery=C5/'delivery.json',fastboot_operator=OP/'fastboot-operator.py',fastboot_operator_delivery=OP/'delivery.json',
  compressed_profile=REF/'charging-oem-audit-20261023/irq-postboot-compressed-profile/profile.py',
  compressed_profile_delivery=REF/'charging-oem-audit-20261023/irq-postboot-compressed-profile/delivery.json')
 baseline.update({key:dict(path=str(path.resolve()),sha256=sha(path.read_bytes()),bytes=path.stat().st_size) for key,path in paths.items()})
 names=['sources.py','controller.py','fastboot-operator.py','remote.py','supervisor.py','common.py','proof.py','eud-quiesce.py','eud-restart.py','prepare-contract.json','host-extra.py.inc','prepare.py']
 emit('source-pins.json',json.dumps(dict(schema='samurai-irq-native-usb-pm-rollback-restart-host-sources-v1',baseline=baseline,
  local={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in names}),indent=2)+'\n')
 exact=[name for name,text in functions((OLD/'controller.py').read_text()).items() if functions(controller).get(name)==text]
 emit('source-reuse.json',json.dumps(dict(passed=True,device_files_byte_exact=['common.py','proof.py','eud-quiesce.py','eud-restart.py'],
  original_controller_adapter_functions=exact,owner='current frozen C5 with unchanged process scheduling functions',
  supervisor_byte_exact=True,remote_preflight_byte_exact_current_two_fd_cleanup=True,
  operator='current logdump-only original command/worker lifecycle, rollback actions only',explicit_private_run=True,device_accessed=False),indent=2)+'\n')
 print(json.dumps(dict(prepared=True,device_accessed=False,runtime_request_created=False)))
if __name__=='__main__':main()
