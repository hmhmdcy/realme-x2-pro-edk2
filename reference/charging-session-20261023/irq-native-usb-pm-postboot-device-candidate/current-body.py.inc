def configure_profile(request):
 global EXPECTED_VERSION,EXPECTED_LOGDUMP,EXPECTED_IMAGE,EXPECTED_REVISION,COHORT_MANIFEST,COHORT_EXPECTED_MANIFEST,COHORT_NOTES
 assert request['profile'] in PROFILES,'explicit postboot profile'
 row=PROFILES[request['profile']]
 EXPECTED_VERSION=row['version'];EXPECTED_LOGDUMP=row['logdump'];EXPECTED_IMAGE=row['image']
 COHORT_MANIFEST=row['manifest_sha256'];COHORT_EXPECTED_MANIFEST=row['manifest'];COHORT_NOTES=row['notes']
 EXPECTED_REVISION=row['manifest']['adapter_revision']
 return row

def validate_request(request):
 row=configure_profile(request);g=request['guard'];stage=request['stage'];a=request['activation_guard']
 assert request['schema']=='samurai-irq-native-usb-pm-postboot-readonly-v1'
 assert request['original_key_transport_verified'] is True and request['new_endpoint']=='fe80::62:bcff:fe28:a101%29'
 assert all(re.fullmatch('[0-9a-f]{64}',request[key]) for key in ['context_sha256','guard_sha256','stage_result_sha256'])
 assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',request['new_boot_id'])
 assert g['new_boot_id']==request['new_boot_id'] and g['boot_id']==a['boot_id']!=request['new_boot_id']
 assert g['target_kernel_version']==row['version'] and g['candidate_boot_sha256']==IRQ_BOOT and g['partitions']==['logdump']
 assert g['candidate_logdump_sha256']==row['logdump'] and g['image_sha256']==row['image']
 assert g['transaction_id']==stage['transaction_id'] and a['transaction_id']==request['activation_transaction_id']
 assert stage['terminal'] is stage['runtime_pending'] is stage['stop_verified'] is True and stage['primary_error'] is None
 assert not stage.get('receipt_error') and not stage.get('close_error')
 if request['profile']=='forward_504':
  assert re.fullmatch(r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}',a['transaction_id'])
  assert re.fullmatch(r'irq-native-usb-pm-stage-[a-z0-9-]{8,48}',stage['transaction_id'])
  assert g['source_kernel_version']==a['source_kernel_version']==PROFILES['restored_502']['version']
  assert a['kernel_version']==row['version']
  assert stage['schema']=='samurai-irq-native-usb-pm-stage-result-v1' and stage['staged'] is True
  assert stage['status']=='staged/runtime_pending' and stage['disk_state']=='all_new_fsynced'
  assert stage['old_manifest_sha256']==PROFILES['restored_502']['manifest_sha256'] and stage['new_manifest_sha256']==row['manifest_sha256']
  assert not stage.get('recovery_error')
 else:
  assert re.fullmatch(r'irq-native-usb-pm-rollback-activate-[a-z0-9-]{8,48}',a['transaction_id'])
  assert re.fullmatch(r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}',stage['transaction_id'])
  assert g['source_kernel_version']==a['kernel_version'] and g['source_kernel_version'] in [p['version'] for p in PROFILES.values()]
  assert stage['schema']=='samurai-irq-native-usb-pm-cold-rollback-result-v1' and stage['restored'] is True
  assert stage['status']=='staged_original/runtime_pending' and stage['disk_state']=='all_original_fsynced'
  assert stage['unknown_write_state'] is False
 return row

def check_partitions(r):
 assert r['boot_partition']['bytes']==100663296 and r['boot_partition']['sha256']==IRQ_BOOT
 assert r['logdump_partition']['bytes']==67108864 and r['logdump_partition']['sha256']==EXPECTED_LOGDUMP
 return dict(bootedd_exact=True,logdump_exact=True,image_sha256=EXPECTED_IMAGE,
  Image_binding='exact complete FAT plus frozen incremental Image receipt')

def collect_pm_topology():
 controller=Path('/sys/bus/platform/devices/a600000.usb').resolve(strict=True)
 provider=Path('/sys/class/power_supply/samurai-usb-input/device').resolve(strict=True)
 return dict(controller=pm_snapshot(controller),provider=pm_snapshot(provider))

def check_pm_topology(raw,request):
 row=PROFILES[request['profile']];topology=raw['native_pm'];controller=topology['controller'];provider=topology['provider']
 assert controller['path'].startswith('/sys/devices/platform/') and controller['path'].endswith('/a600000.usb')
 assert controller['of_node']=='/sys/firmware/devicetree/base/soc@0/usb@a6f8800/usb@a600000'
 assert controller['compatible'].rstrip('\0')=='snps,dwc3' and controller['usb_psy_name'].rstrip('\0')=='samurai-usb-input'
 assert provider['path']==raw['irq_before']['device']==raw['irq_after']['device'] and provider['of_node']==NODE
 assert controller['power']['control']=='on' and controller['power']['runtime_status']=='active','current DEVICE/on/active premise'
 forward=[link for link in controller['links'] if link.get('supplier')==provider['path']]
 reverse=[link for link in provider['links'] if link.get('consumer')==controller['path']]
 if row['system_pm_link']:
  assert len(forward)==len(reverse)==1
  assert forward[0]['target']==reverse[0]['target'] and forward[0]['consumer']==controller['path'] and reverse[0]['supplier']==provider['path']
  for link in forward+reverse:
   assert link['runtime_pm']=='0' and link['sync_state_only']=='0' and link['status']=='not tracked','stateless-only native dependency'
 else:assert not forward and not reverse,'restored original native provider has no added PM link'
 return dict(native_DEVICE_on_active=True,stateless_dependency_observed=bool(forward),
  expected_dependency=row['system_pm_link'],system_suspend_or_resume_or_USB_recovery_accepted=False)

def check_cache(raw):
 before,after=raw['protection_cache_before'],raw['protection_cache_after']
 validate_cache(before);validate_cache(after);assert before==after,'same held protection instance/cache'
 return dict(same_readonly_cache_instance=True,new_capture_issued=False)

def collect(request,raw=None):
 validate_request(request)
 if raw is None:raw={}
 start=time.clock_gettime_ns(time.CLOCK_BOOTTIME);prior=identity();check_identity(prior,request['guard'])
 reader=CacheReader()
 try:
  reader.open_cache();raw['protection_cache_before']=reader.cache_evidence()
  collect_base(request,raw)
  raw['native_pm']=attempt(collect_pm_topology)
  raw['protection_cache_after']=reader.cache_evidence()
  raw['identity_after']=identity();raw['started_boottime_ns']=start
  raw['ended_boottime_ns']=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
  return raw
 finally:reader.close()

def main(argv=None,request=None):
 if sys.flags.optimize:raise RuntimeError('optimized Python disables required checks')
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--check-local',action='store_true');p.add_argument('--execute',action='store_true')
 p.add_argument('--window-confirmed',action='store_true');p.add_argument('--new-endpoint');args=p.parse_args(argv)
 if not args.execute:
  print(json.dumps(dict(local_checks_passed=True,device_accessed=False,read_only=True)));return 0
 assert args.window_confirmed and args.new_endpoint and request is not None
 assert request['new_endpoint']==args.new_endpoint;validate_request(request)
 raw={}
 try:collect(request,raw);result=audit(raw,request)
 except Exception as error:result=dict(passed=False,read_only=True,collection_error=type(error).__name__,message=str(error))
 print(json.dumps(dict(schema=request['schema'],profile=request['profile'],transaction_id=request['guard']['transaction_id'],
  context_sha256=request['context_sha256'],guard_sha256=request['guard_sha256'],raw=raw,result=result)),flush=True)
 return 0 if result['passed'] else 1
