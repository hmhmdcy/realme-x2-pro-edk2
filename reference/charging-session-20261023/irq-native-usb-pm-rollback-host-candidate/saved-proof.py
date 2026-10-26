"""Read saved source and exact original logdump commands. No USB dispatch."""
from pathlib import Path
from types import SimpleNamespace
import copy,hashlib,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current_rollback_shared',HERE/'shared.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
need=shared.need;local=shared.local;load_module=shared.load;source_check=shared.source_check
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
read_json=lambda path:json.loads(Path(path).read_bytes())
load=read_json
OPERATOR_PATH=HERE.parent/'irq-native-usb-pm-activation-device-candidate/fastboot-operator.py'
def saved_command(directory,label,argv):
 directory=Path(directory)
 command=load(directory/(label+'-command-private.json'))
 child=load(directory/(label+'-process-private.json'))
 terminal=load(directory/(label+'-terminal-private.json'))
 need(command=={'requested_argv':argv,'request_count':1},'original command claim differs: '+label)
 need(type(child['pid']) is int and child['pid']>0 and child['requested_argv']==argv,'original child differs: '+label)
 observed=child['observed']
 need(observed['pid']==child['pid'] and type(observed['startticks']) is int
  and observed['startticks']>0 and observed['argv'],'actual captured child identity missing: '+label)
 need(terminal['pid']==child['pid'] and terminal['requested_argv']==argv
  and terminal['terminal'] is True and type(terminal['returncode']) is int and terminal['returncode']==0,
  'same child actual terminal0 missing: '+label)
 out,err=directory/(label+'-stdout-private.bin'),directory/(label+'-stderr-private.bin')
 need(sha(out)==terminal['stdout_sha256'] and sha(err)==terminal['stderr_sha256'],'original command output changed: '+label)
 return out.read_bytes().decode(errors='replace'),err.read_bytes().decode(errors='replace')

def review_action(operator,context_path,context,action):
 base=Path(context_path).resolve().parent/'fastboot-operator'
 directory=base/action
 request_path=directory/'request-private.json';result_path=directory/'result-private.json'
 request,result=load(request_path),load(result_path)
 expected={'transaction_id':context['transaction_id'],'token':context['token'],'old_boot_id':context['old_boot_id'],
           'context_sha256':sha(context_path)}
 need(request['schema']=='samurai-irq-native-usb-pm-fastboot-action-v1' and request['execute_authorized'] is True
  and request['window_confirmed'] is True and request['action']==action
  and request['operator_sha256']==sha(OPERATOR_PATH) and request['inputs']==operator.local_inputs(),
  'actual action source/context inputs differ')
 need(type(request['claimed_ns']) is int and request['claimed_ns']>0,'actual action time missing')
 need(all(request[k]==result[k]==v for k,v in expected.items()) and result['action']==action
  and result['claimed_ns']==request['claimed_ns'] and result['terminal'] is True
  and result['passed'] is True and result['commands_terminal'] is True,'action not bound successful terminal')
 serial=operator.read_json(operator.IDENTITY)['serial'];seen=[]
 def retained_call(label,argv):
  seen.append(label);return saved_command(directory,label,argv)
 replay=operator.run_action(action,serial,retained_call)
 need(all(result.get(k)==v for k,v in replay.items()),'actual saved output/result differs')
 need({p.name.removesuffix('-command-private.json') for p in directory.glob('*-command-private.json')}==set(seen),
  'unknown or omitted original command')
 if action in operator.REBOOT_IMAGES:
  binding=operator.reboot_binding(base,action)
  need(request['image_binding']==result['image_binding']==binding,'original reboot/write claim binding differs')
 return {'request_sha256':sha(request_path),'result_sha256':sha(result_path),'claimed_ns':request['claimed_ns'],
         'command_labels':seen,'all_original_children_terminal0':True,'result':result}

def review_profile_sources(profile,stage_directory,stage_fetch_directory,context_path=None):
 pins=source_check();worker=load_module(pins['worker']['path'],'current_cold_rollback_profiles')
 need(profile in worker.PROFILES,'explicit current rollback profile')
 retained=load_module(pins['retained']['path'],'actual_retained_source_reviewer')
 source=retained.review_retained_stage(stage_directory,stage_fetch_directory);stage=source['stage_review']
 projection=stage['stage'];identity=stage['request']['identity'];activation=None;selected=None
 call=local(stage_fetch_directory);response=json.loads((call/'received-result-private.json').read_bytes())
 observations={'worker':response['process'],'supervisor':response['supervisor_process']}
 need(all(value['state'] in ['absent','zombie'] for value in observations.values()),'actual saved source-frame process observation')
 if profile==worker.PROFILES[0]:need(context_path is None,'same-boot branch uses no activation')
 else:
  need(context_path is not None,'selected original activation records required')
  path=local(context_path);operator=operator_for_past_context(stage,stage_directory,stage_fetch_directory)
  context=operator.validate_context(path)
  need(context['stage_directory']==str(local(stage_directory)) and context['stage_fetch_directory']==str(local(stage_fetch_directory)),
   'selected activation/source stage directories differ')
  directory=path.parent/'fastboot-operator';operator.prior_terminal(directory,'inspect')
  pair=['flash-candidate','reboot-candidate'] if profile==worker.PROFILES[1] else ['rollback-original','reboot-original']
  flash=review_action(operator,path,context,pair[0]);reboot=review_action(operator,path,context,pair[1])
  need(flash['claimed_ns']<reboot['claimed_ns'],'original write must precede selected reboot')
  opposing=['rollback-original','reboot-original'] if profile==worker.PROFILES[1] else ['flash-candidate','reboot-candidate']
  for name in opposing:
   if (directory/name).exists():
    claim=read_json(directory/name/'request-private.json')
    need(type(claim['claimed_ns']) is int and claim['claimed_ns']<flash['claimed_ns'],'later opposing action invalidates selected profile')
  guard=read_json(operator.reference_file(path.parent,context['files']['guard']))
  need(guard['stage']==projection and guard['boot_id']==identity['boot_id'] and
   guard['source_kernel_version']==identity['version'],'original activation belongs to source stage')
  selected=dict(flash=flash,reboot=reboot)
  activation=dict(schema='samurai-irq-native-usb-pm-saved-activation-v1',activation_transaction_id=context['transaction_id'],
   context_sha256=sha(path),guard_sha256=context['guard_sha256'],flash_request_sha256=flash['request_sha256'],
   flash_result_sha256=flash['result_sha256'],reboot_request_sha256=reboot['request_sha256'],reboot_result_sha256=reboot['result_sha256'],
   flash_claimed_ns=flash['claimed_ns'],reboot_claimed_ns=reboot['claimed_ns'],boot_sha256=worker.BOOT,
   logdump_sha256=worker.LOGDUMP504 if profile==worker.PROFILES[1] else worker.LOGDUMP502,action_pair=pair)
 return dict(schema='samurai-irq-native-usb-pm-saved-source-review-v1',profile=profile,source_identity=identity,
  source_stage=projection,source_stage_observations=observations,activation=activation,saved_selected_actions=selected,
  source_stage_terminal_authenticated=True,current_identity_or_health_verified=False,
  current_global_pointer_consulted=False,device_or_transport_accessed=False)

def operator_for_past_context(stage,stage_directory,stage_fetch_directory):
 pins=source_check();operator=load_module(pins['operator']['path'],'original_current_logdump_operator_readonly_replay')
 text=inspect.getsource(operator.validate_context)
 before="""    import importlib.util
    spec=importlib.util.spec_from_file_location('current_irq_stage_review',HERE/'stage-proof.py')
    proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)"""
 need(text.count(before)==1,'original seven-file context reviewer shape changed')
 def review_stage(actual_stage,actual_fetch):
  need(local(actual_stage)==local(stage_directory) and local(actual_fetch)==local(stage_fetch_directory),
   'only the already source-authenticated retained stage')
  return copy.deepcopy(stage)
 api=SimpleNamespace(review_stage=review_stage,guard_stage_fields=lambda value:copy.deepcopy(value['stage']))
 namespace=dict(operator.__dict__);namespace['retained_stage_api']=lambda:api
 exec(compile(text.replace(before,'    proof=retained_stage_api()'),'<past-original-context-review>','exec'),namespace)
 operator.validate_context=namespace['validate_context']
 return operator

if __name__=='__main__':
 source_check();print(json.dumps({'source_only':True,'device_accessed':False,'runtime_request_created':False}))
