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
