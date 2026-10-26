"""Read saved completed IRQ boot actions. Never calls USB or dispatches a child."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()

def need(value,message):
 if not value:raise ValueError(message)

def load(path):return json.loads(Path(path).read_bytes())

def source_module():
 delivery=load(HERE/'delivery.json')
 need(delivery['passed'] is True and delivery['frozen'] is True,'final frozen operator required')
 for name in ['fastboot-operator.py','source-pins.json','completion-proof.py']:
  need(sha(HERE/name)==delivery['files'][name]['sha256'],'completion source changed: '+name)
 spec=importlib.util.spec_from_file_location('irq_actual_boot_operator',HERE/'fastboot-operator.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

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
 need(request['schema']=='samurai-usb-irq-protection-fastboot-action-v1' and request['execute_authorized'] is True
  and request['window_confirmed'] is True and request['action']==action
  and request['operator_sha256']==sha(HERE/'fastboot-operator.py') and request['inputs']==operator.local_inputs(),
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

def review_completed_activation(context_path):
 operator=source_module();context_path=Path(context_path)
 context=operator.validate_context(context_path)
 base=context_path.resolve().parent/'fastboot-operator'
 # This examines each consumed intent. A partial or unknown earlier action is
 # not bypassed just because a later result file says passed.
 operator.prior_terminal(base,'inspect')
 flash=review_action(operator,context_path,context,'flash-candidate')
 reboot=review_action(operator,context_path,context,'reboot-candidate')
 need(flash['claimed_ns']<reboot['claimed_ns'],'reboot predates exact candidate write')
 for other in ('rollback-original','reboot-original'):
  if (base/other).exists():
   request=load(base/other/'request-private.json')
   need(request['claimed_ns']<flash['claimed_ns'],'later original/rollback action prevents candidate qualification')
 guard=load(operator.reference_file(context_path.resolve().parent,context['files']['guard']))
 return {'schema':'samurai-usb-irq-protection-completed-activation-review-v1',
         'activation_transaction_id':context['transaction_id'],'context':context,'guard':guard,
         'source_boot_id':context['old_boot_id'],'partitions_written':['boot'],
         'candidate_boot_sha256':operator.IRQ_BOOT,'retained_logdump_sha256':operator.LOGDUMP502,
         'context_sha256':sha(context_path),'guard_sha256':context['guard_sha256'],
         'flash':flash,'reboot':reboot,'saved_activation_commands_verified':True,
         'new_boot_or_hardware_readback_verified':False,'rootfs_rollback_proven':False,
         'device_or_transport_accessed':False}
