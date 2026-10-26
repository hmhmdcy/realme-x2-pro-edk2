def rollback_material(meta):
 global _ROLLBACK_MODULE,_RESTORED_AFTER,_CACHE_EXPECTED
 proof_path=secure_file(ROOT/meta['transaction_id']/'proof.py')
 need(file_sha(proof_path)==PROOF_SHA,'pinned rollback qualifier')
 proof=runpy.run_path(str(proof_path)); rollback=meta['rollback']
 need(set(rollback)=={'transaction_id','request_sha256','result_sha256','host_binding_sha256','worker_sha256','supervisor_sha256','evidence'},'rollback evidence fields')
 paths=proof['remote_paths'](rollback['transaction_id'])
 need(set(paths)==set(rollback['evidence']),'exact rollback evidence set')
 raw={}
 for key,path in paths.items():
  item=rollback['evidence'][key]
  need(item=={'path':path,'sha256':item['sha256']} and re.fullmatch('[0-9a-f]{64}',item['sha256']),'canonical rollback path/hash')
  raw[key]=raw_owned(path,limit=8_000_000)
  need(sha(raw[key])==item['sha256'],'rollback original changed: '+key)
 need(sha(raw['request'])==rollback['request_sha256'] and sha(raw['result'])==rollback['result_sha256'],'rollback request/result')
 need(sha(raw['worker_source'])==rollback['worker_sha256']==proof['WORKER'] and
  sha(raw['supervisor_source'])==rollback['supervisor_sha256']==proof['SUPERVISOR'],'original rollback sources')
 root=owned_directory(ROOT/rollback['transaction_id']);owned_directory(root/'device-rollback')
 worker=runpy.run_path(str(root/'restore-worker.py'))
 from types import SimpleNamespace
 module=SimpleNamespace(**worker);request=json.loads(raw['request']);result=json.loads(raw['result'])
 names={'result':'result.json','worker_process':'process-private.json','worker_launch':'worker-launch-receipt-private.json',
  'worker_terminal':'worker-terminal-private.json','supervisor_launch':'launch-receipt-private.json',
  'supervisor_process':'supervisor-process-private.json','supervisor_terminal':'supervisor-terminal-private.json',
  'before':'before-private.json','stopped':'stopped-private.json','after':'after-private.json'}
 process={}
 for key,role in [('worker_process','process'),('supervisor_process','supervisor_process')]:
  observed=process_observation(json.loads(raw[key]));process[role]=observed
 response={'transaction_id':request['transaction_id'],'request_sha256':sha(raw['request']),
  'worker_terminal_verified':True,'worker_terminal':json.loads(raw['worker_terminal']),'worker_result':result,
  'files':{name:{'base64':base64.b64encode(raw[key]).decode(),'bytes':len(raw[key]),'sha256':sha(raw[key])} for key,name in names.items()},**process}
 proof['validate_records'](request,raw['request'],response,module)
 need(request['identity']=={'boot_id':meta['boot_id'],'version':meta['kernel_version'],
  'serial_sha256':meta['soc_serial_sha256'],'compatible_sha256':meta['compatible_sha256'],
  'rootfs_sha256':meta['rootfs_release_sha256']} and request['profile']==meta['profile'],'current rollback identity')
 # The frozen source verifier is read-only except for one evidence-log call.
 # Reuse its actual verifier with only that log sink suppressed; no Device.begin,
 # stop, replace, close or publish method is called here.
 reader=SimpleNamespace(log=lambda name,value:None)
 module.Device.source_proof(reader,request)
 expected=module.expected_profile(request)
 need(meta['current_boot_sha256']==expected['boot'] and meta['current_logdump_sha256']==expected['logdump'] and
  meta['resident_notes']==expected['notes'] and meta['current_cache']==request['current_cache'],'explicit current rollback profile')
 _ROLLBACK_MODULE=module;_RESTORED_AFTER=json.loads(raw['after']);_CACHE_EXPECTED=request['current_cache']
 return request,module


def validate_meta_shape(meta,guard_path):
 need(guard_path.is_absolute() and guard_path.name=='guard-private.json','private guard path')
 need(set(meta)=={'schema','transaction_id','token','boot_id','kernel_release','kernel_version','soc_serial_sha256',
  'compatible_sha256','rootfs_release_sha256','profile','current_boot_sha256','rollback_logdump_sha256',
  'unchanged_boot_sha256','current_logdump_sha256','current_cache','boot_bytes','logdump_bytes','resident_notes','rollback','post_restore_probe',
  'partitions','disk_state','runtime_validation_accepted'},'exact rollback restart fields')
 need(meta['schema']=='samurai-irq-native-usb-pm-rollback-restart-v1' and
  re.fullmatch(r'irq-native-usb-pm-rollback-activate-[a-z0-9-]{8,48}',meta['transaction_id']) and
  re.fullmatch('[0-9a-f]{48}',meta['token']),'new rollback restart identity')
 need(meta['transaction_id']!=meta['rollback']['transaction_id'] and guard_path.parent==ROOT/meta['transaction_id'],'independent restart directory')
 need(meta['kernel_release']==RELEASE and meta['kernel_version'] in (VERSION,VERSION504) and meta['partitions']==['logdump'] and
  meta['rollback_logdump_sha256']==LOGDUMP and meta['unchanged_boot_sha256']==BOOT and meta['current_boot_sha256']==BOOT and
  meta['boot_bytes']==100663296 and meta['logdump_bytes']==67108864 and
  meta['disk_state']=='all_original_fsynced' and meta['runtime_validation_accepted'] is False,'fixed rollback target and pending runtime')
 need(set(meta['post_restore_probe'])=={'stdin_sha256','stdout_sha256','child_sha256','terminal_sha256'} and
  all(re.fullmatch('[0-9a-f]{64}',v) for v in meta['post_restore_probe'].values()),'actual post-restore probe digests')


def validate_activation_guard(guard_path,allow_inhibit=False):
 global OLD_NOTES
 need(os.geteuid()==0 and not sys.flags.optimize,'root nonoptimized worker')
 guard_path=secure_file(guard_path);meta=json.loads(raw_owned(guard_path));validate_meta_shape(meta,guard_path)
 owned_directory(guard_path.parent);acquire_service_lock()
 need(str(uuid.UUID(meta['boot_id']))==meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'same actual rollback boot')
 need(os.uname().machine=='aarch64' and os.uname().release==RELEASE and os.uname().version==meta['kernel_version'],'exact actual current profile kernel')
 need(Path('/proc/sys/kernel/tainted').read_text().strip()=='0','taint')
 need(file_sha('/etc/samurai-rootfs-release')==meta['rootfs_release_sha256'],'rootfs')
 serial=Path('/sys/devices/soc0/serial_number').read_bytes();compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
 need(serial.strip() and sha(serial)==meta['soc_serial_sha256'] and sha(compatible)==meta['compatible_sha256'] and
  b'realme,samurai' in compatible.split(b'\0'),'board identity')
 request,worker=rollback_material(meta)
 need(block_sha('/dev/disk/by-partlabel/boot',100663296)==meta['current_boot_sha256'] and
  block_sha('/dev/disk/by-partlabel/logdump',67108864)==meta['current_logdump_sha256'],'current complete carriers')
 need(file_sha('/usr/share/samurai-charging/manifest.json')==OLD,'restored original R8 manifest')
 manifest=json.loads(Path('/usr/share/samurai-charging/manifest.json').read_bytes())
 need(manifest==EXPECTED_MANIFEST,'exact restored R8 structure')
 for path,digest in manifest['installed_files'].items():need(file_sha(path)==digest,'original/retained installed file: '+path)
 for path,digest in OLD_FILES.items():need(sha(raw_owned(path))==digest,'actual original restored file')
 OLD_NOTES=dict(worker.expected_profile(request)['notes'])
 verify_current_cache(meta['current_cache'])
 need(meta['resident_notes']==OLD_NOTES,'explicit still-resident profile')
 for name,digest in OLD_NOTES.items():
  node=Path('/sys/module',name.replace('-','_'))
  need(sha((node/'notes/.note.gnu.build-id').read_bytes())==digest and (node/'initstate').read_text().strip()=='live','actual resident profile')
 need(Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y' and
  not Path('/sys/module/samurai_usbin_init').exists(),'retained native provider/no helper')
 need(file_sha(STARTUP_PATH)==STARTUP_SHA and Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text().strip()=='500','startup/descriptor500')
 need(Path('/sys/module/bq27xxx_battery/parameters/samurai_instant_current').read_text().strip()=='Y' and
  [v for v in Path('/proc/cmdline').read_text().split() if v.startswith('bq27xxx_battery.samurai_instant_current=')]==['bq27xxx_battery.samurai_instant_current=1'],'instant current opt-in')
 eud_off_check();camera481_check(guard_path.parent/'camera481-expected-private.json')
 data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME));verify_current_cache(meta['current_cache'])
 if not allow_inhibit:environment(data)
 phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json')
 need(not phase.exists(),'restart already claimed; retain original evidence')
 return meta,Path('/var/lib/samurai')/meta['transaction_id'],phase
