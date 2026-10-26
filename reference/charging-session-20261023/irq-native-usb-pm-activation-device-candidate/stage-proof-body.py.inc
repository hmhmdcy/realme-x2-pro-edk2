def review_stage(stage_directory,fetch_directory):
 pins,values=source_check();host=load(local(pins['stage_host']['path']),'current_stage_host_originals')
 stage=local(stage_directory);call=local(fetch_directory)
 need(call.parent==stage and re.fullmatch(r'fetch-[0-9a-f]{16}-private',call.name),'one explicit original fetch directory')
 out,binding,request,request_raw,host_pins=host.bound(stage.name,launching=True)
 need(local(out)==stage and binding['reviewed']['manifest_sha256']==SOURCE_MANIFEST,'actual current stage binding')
 aliases={'update_host':pins['stage_host'],'update_supervisor':pins['stage_supervisor']}
 response,raw=fetch_raw(call,request_raw,aliases,{'update_remote':values['stage_remote']})
 process_chain(response,raw,request,request_raw)
 need(raw['request-private.json']==request_raw and response['worker_result']==json.loads(raw['result.json']),'actual executed stage result/request')
 common=load(HERE/'common.py','current_stage_device_receipt_rules')
 evidence={};records={}
 binary={'old_usb','old_manifest'}
 for key,path in common.stage_paths(stage.name).items():
  if key=='worker_source':data=(stage/'stage-worker.py').read_bytes()
  elif key=='supervisor_source':data=values['stage_supervisor']
  elif key=='request':data=request_raw
  else:data=raw[Path(path).name]
  evidence[key]={'path':path,'sha256':sha(data)}
  if key not in ['worker_source','supervisor_source']:records[key]=data if key in binary else json.loads(data)
 fields={'transaction_id':stage.name,'request_sha256':sha(request_raw),'result_sha256':sha(raw['result.json']),
  'host_binding_sha256':sha((stage/'binding-private.json').read_bytes()),'worker_sha256':pins['stage_worker']['sha256'],
  'supervisor_sha256':pins['stage_supervisor']['sha256'],'evidence':evidence}
 identity=request['identity']
 meta=dict(stage=fields,boot_id=identity['boot_id'],soc_serial_sha256=identity['serial_sha256'],
  compatible_sha256=identity['compatible_sha256'],rootfs_release_sha256=identity['rootfs_sha256'],adoption=request['adoption'])
 observed={k:dict(response[k+'_process'] if k=='supervisor' else response['process']) for k in ['worker','supervisor']}
 # Host has the original transfer and two true wait receipts. The original
 # device launch-claim is not exported by R2. It is reread independently by
 # read_stage() on the phone; this reviewer does not fabricate that raw file.
 common.validate_stage_receipts(meta,records,observed)
 for k,v in [('boot_id',identity['boot_id']),('guard_path',request['adoption']['guard_path']),('guard_sha256',request['adoption']['guard_sha256'])]:
  need(binding['reviewed'][k]==v,'current runtime source identity differs')
 return {'schema':'samurai-irq-native-usb-pm-stage-review-v1','stage':fields,'request':request,
  'source_review_inputs':binding['source_review_inputs'],'source_runtime':binding['reviewed'],
  'stage_directory':str(stage),'stage_fetch_directory':str(call),
  'device_launch_claim_not_exported':True,'actual_device_launch_claim_still_required':True}

def guard_stage_fields(review):
 need(review['schema']=='samurai-irq-native-usb-pm-stage-review-v1','current stage review required')
 return copy.deepcopy(review['stage'])
