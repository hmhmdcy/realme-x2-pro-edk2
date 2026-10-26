"""Derive offline 502 tools from frozen 501 sources. No device or valid contract."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/gauge-image501-activation-candidate'
PAIR=REF/'charging-session-20261023/gauge-image501-fastboot-pair-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PINS={'controller.py':'bff36b8596d80d737be195d471b37c169673e4e50b9692cc8921344b4e02bbf7',
 'guard-fragment.py':'8837af79bdbbceecbf7a253f57c6e4cb1bab9b8764f4deb72b042d533b450432',
 'eud-quiesce.py':'3830ffd16173b24b9ee859818e3c5a64f9144e4a0f36417af14fd7a5a2d733e9',
 'eud-restart.py':'5b9f309417342d297684e0e66766b0ba59e30dd68dfabd74c411a84875df727d',
 'remote.py':'ba0a070fc88777e548a4ae93479f47b621cfb5392b4f9b9f088a840d23001a8a'}
for n,h in PINS.items():assert sha(OLD/n)==h,n
assert sha(PAIR/'fastboot-operator.py')=='21d23cc9ae6ef6eae4a0688c825396e5eeba8cacfde18830eae81ed0631d1e49'
TX='image502-notify-live-001'
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def replace_fn(s,name,new):
 node=next(n for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
 lines=s.splitlines(True);return ''.join(lines[:node.lineno-1])+new.strip()+'\n'+''.join(lines[node.end_lineno:])
def common(s):
 return s.replace('samurai-image501-fastboot-context-v1','samurai-image502-notify-fastboot-context-v1').replace('samurai-image501-activation-v1','samurai-image502-notify-activation-v1').replace("r'image501-[a-z0-9-]{8,64}'", "r'image502-notify-live-001'").replace('image501-activation','image502-notify-activation')
guard=(OLD/'guard-fragment.py').read_text()
guard=common(guard)
guard=replace(guard,"CANDIDATE_BOOT='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'\nROLLBACK_BOOT='4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'", "UNCHANGED_BOOT='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'")
guard=replace(guard,"CANDIDATE_LOGDUMP='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'", "CANDIDATE_LOGDUMP='__MATERIALIZE_LOGDUMP_SHA256__'\nIMAGE502='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'")
guard=guard.replace("IMAGE363='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'\n",'')
guard=guard.replace("LOGDUMP365='aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da'", "LOGDUMP501='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'")
guard=guard.replace('/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt','/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt').replace("startswith('#363 ')","startswith('#501 ')")
guard=replace(guard," assert meta['candidate_boot_sha256']==CANDIDATE_BOOT\n assert meta['rollback_boot_sha256']==ROLLBACK_BOOT and meta['partitions']==['boot','logdump'] and meta['boot_bytes']==100663296", " assert meta['unchanged_boot_sha256']==UNCHANGED_BOOT and meta['partitions']==['logdump'] and meta['boot_bytes']==100663296")
guard=guard.replace("meta['rollback_logdump_sha256']==LOGDUMP365", "meta['rollback_logdump_sha256']==LOGDUMP501")
guard=guard.replace("assert meta['image363_sha256']==IMAGE363 and meta['image501_sha256']==IMAGE501", "assert meta['image501_sha256']==IMAGE501 and meta['image502_sha256']==IMAGE502")
guard=guard.replace('==ROLLBACK_BOOT','==UNCHANGED_BOOT').replace('==LOGDUMP365','==LOGDUMP501')
guard=guard.replace('# Exact FAT partition identity binds its already-verified ::/Image bytes to\n # Image363 (kernel365/prepare-deployment.py); neither partition is written.', '# Current complete FAT identity binds the already verified Image501; both partitions are read-only here.')
guard=replace(guard," assert sample['valid']==sample['online']==sample['protection_ok']==1 and 0<=sample['age_ms']<=3000", " assert sample['valid']==sample['online']==sample['protection_ok']==1 and 0<=sample['age_ms']<=3000\n assert Path('/sys/module/bq27xxx_battery/parameters/samurai_instant_current').read_text().strip()=='Y'\n assert 'bq27xxx_battery.samurai_instant_current=1' in Path('/proc/cmdline').read_text().split()\n full=(sample['logical_full']==sample['hold_requested']==sample['full_holding']==1 and sample['full_cause'] in (1,2,3) and sample['desired_enable']==0 and sample['session_seconds']==0)\n assert full if any(sample[k] for k in ['logical_full','hold_requested','full_holding','full_cause']) else sample['desired_enable']==1\n budget=int(Path('/sys/class/power_supply/samurai-usb-input/current_max').read_text())\n assert budget>=50000 and sample['budget_ua']==budget\n actual=Path('/sys/class/power_supply/mp2650-input')\n assert 50000<=int((actual/'input_current_limit').read_text())<=min(900000,budget)\n assert 200000<=int((actual/'constant_charge_current').read_text())<=250000\n assert 7425000<=int((actual/'constant_charge_voltage').read_text())<=8725000")
guard=replace(guard,'def validate_activation_guard(guard_path):','''def charging_sample_phase(sample, stopped=False):
 full=(sample['logical_full']==sample['hold_requested']==sample['full_holding']==1 and sample['full_cause'] in (1,2,3) and sample['desired_enable']==0 and sample['session_seconds']==0)
 if stopped:
  return sample['desired_enable']==sample['hold_requested']==sample['full_holding']==0 and (sample['logical_full']==0 and sample['full_cause']==0 or sample['logical_full']==1 and sample['full_cause'] in (1,2,3) and sample['session_seconds']==0)
 return full if any(sample[k] for k in ['logical_full','hold_requested','full_holding','full_cause']) else sample['desired_enable']==1

def validate_activation_guard(guard_path, allow_inhibit=False):''')
guard=replace(guard," assert full if any(sample[k] for k in ['logical_full','hold_requested','full_holding','full_cause']) else sample['desired_enable']==1", " stopped=False\n if allow_inhibit:\n  qdir=Path('/var/lib/samurai')/meta['transaction_id']\n  q=json.loads(secure_file(qdir/'state-private.json').read_bytes());summary=json.loads(secure_file(qdir/'summary.json').read_bytes())\n  assert q['terminal'] and q['exit_code']==0 and summary['taint']==0\n  assert all(q[k]==summary[k]==meta[k] for k in ['transaction_id','token','boot_id'])\n  stopped=True\n assert charging_sample_phase(sample,stopped)")
guard=guard.replace('validate_activation_guard(Path(sys.argv[2]))', "validate_activation_guard(Path(sys.argv[2]),allow_inhibit=sys.argv[3] in ['--inspect','--commit-restart2-bootloader'])")
(HERE/'guard-fragment.py').write_text(guard)
for name in ['eud-quiesce.py','eud-restart.py']:
 s=(OLD/name).read_text();oldguard=(OLD/'guard-fragment.py').read_text();assert oldguard in s
 s=s.replace(oldguard,guard);s=common(s)
 s=s.replace('from pathlib import Path\n','from pathlib import Path\nimport sys\nif sys.flags.optimize:raise RuntimeError("optimized interpreter is unsupported")\n',1)
 (HERE/name).write_text(s)

controller=common((OLD/'controller.py').read_text())
controller=controller.replace('One Image501 pair activation host journal.','One Image502 logdump-only activation host journal.')
controller=replace(controller,"WORKERS=HERE", "MATERIALIZED=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-materialized-001')\nWORKERS=MATERIALIZED")
controller=controller.replace("/charging-management-20261023/image501-activation'", "/charging-management-20261023/image502-notify-activation'")
controller=replace(controller,"WORKER_HASHES={'eud-quiesce.py':'3830ffd16173b24b9ee859818e3c5a64f9144e4a0f36417af14fd7a5a2d733e9',\n 'eud-restart.py':'5b9f309417342d297684e0e66766b0ba59e30dd68dfabd74c411a84875df727d'}", 'WORKER_HASHES={}')
controller=controller.replace('sys.dont_write_bytecode=True','if sys.flags.optimize:raise RuntimeError("optimized interpreter is unsupported")\nsys.dont_write_bytecode=True',1)
controller=replace_fn(controller,'profile',r'''
def profile(raw):
 adopted=json.loads(raw['adoption']);endpoint=json.loads(raw['endpoint']);post=json.loads(raw['postboot_501'])
 assert adopted['passed'] and adopted['guard_created'] and adopted['pointer']['Image501_verified']
 a=adopted['pointer'];before,after=post['raw']['identity_before'],post['raw']['identity_after']
 assert post['result']['passed'] and post['result']['read_only'] and post['result']['hardware_writes']==0 and before==after
 assert before['boot_id']==endpoint['observed_new_boot'] and before['uname']['version'].startswith('#501 ')
 assert endpoint['postboot_Image501_passed'] and endpoint['original_key_verified'] and a['original_key_verified']
 assert a['guard_path']==endpoint['guard_path']=='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
 assert a['postboot_raw_sha256']==sha(raw['postboot_501'])
 assert a['candidate_boot_sha256']==post['raw']['boot_partition']['sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
 assert a['candidate_logdump_sha256']==post['raw']['logdump_partition']['sha256']=='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
 assert a['charging_manifest_sha256']==post['raw']['manifest']['sha256']=='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
 for name in ['old501_flash_terminal','old501_reboot_terminal']:
  terminal=json.loads(raw[name]);assert terminal['passed'] and terminal['terminal'] and terminal['commands_terminal']
  assert terminal['transaction_id']=='image501-gauge-live-001' and terminal['old_boot_id']!=before['boot_id']
  assert terminal['context_sha256']==post['context_sha256']
 flash=json.loads(raw['old501_flash_terminal'])
 assert flash['partitions_written']==['logdump','boot'] and flash['pair_complete'] and flash['flashed_pair_sha256']=={'boot':a['candidate_boot_sha256'],'logdump':a['candidate_logdump_sha256']}
 assert endpoint['kind']=='usb-ipv6' and endpoint['peer']=='fe80::62:bcff:fe28:a101%29' and endpoint['interface_index']==29 and endpoint['host_key_alias']=='169.254.42.1'
 return {'identity':before,'board':{'serial_sha256':before['serial_sha256'],'compatible_sha256':sha(base64.b64decode(before['compatible_b64'],validate=True))}}
''')
controller=replace_fn(controller,'local_inputs',r'''
def local_inputs(require_tests=True):
 spec=importlib.util.spec_from_file_location('image502_materialization',HERE/'materialize.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 bundle=m.validate_bundle(MATERIALIZED)
 pins=load_json(HERE/'baseline-input-pins.json');raw={}
 for name,p in pins.items():
  value=Path(p['path']).read_bytes();assert sha(value)==p['sha256'];raw[name]=value
 profile(raw)
 global WORKER_HASHES
 WORKER_HASHES=dict(bundle['worker_hashes'])
 for name,digest in WORKER_HASHES.items():assert sha((WORKERS/name).read_bytes())==digest
 return pins,raw
''')
controller=controller.replace("e['postboot_R3_passed']", "e['postboot_Image501_passed']")
(HERE/'controller.py').write_text(controller)
remote=common((OLD/'remote.py').read_text()).replace('from pathlib import Path\n','from pathlib import Path\nimport sys\nif sys.flags.optimize:raise RuntimeError("optimized interpreter is unsupported")\n',1)
remote=remote.replace("ns['validate_activation_guard'](root/'guard-private.json')", "ns['validate_activation_guard'](root/'guard-private.json',allow_inhibit=d['action'] in ['inspect-restart','restart'])")
(HERE/'remote.py').write_text(remote)

operator=common((PAIR/'fastboot-operator.py').read_text())
operator=operator.replace('One-shot two-partition Image501','One-shot logdump-only Image502')
operator=operator.replace("read_json(HERE / 'activation-pins.json')", "read_json(ACTIVATION / 'activation-pins.json')")
operator=operator.replace('sys.dont_write_bytecode = True','if sys.flags.optimize:raise RuntimeError("optimized interpreter is unsupported")\nsys.dont_write_bytecode = True',1)
start=operator.index('CARRIERS = ');end=operator.index('# Explicit two-file operation',start)
operator=operator[:start]+'''MATERIALIZED = PRIVATE / 'image502-notify-materialized-001'
ACTIVATION = MATERIALIZED
IMAGES = {}
SIZES = {'boot': 100663296, 'logdump': 67108864}
'''+operator[end:]
operator=replace_fn(operator,'local_inputs',r'''
def local_inputs():
    import importlib.util
    spec=importlib.util.spec_from_file_location('image502_logdump_materialization',HERE/'materialize.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    bundle=m.validate_bundle(MATERIALIZED)
    global IMAGES
    IMAGES={which:{'logdump':(Path(row['path']),row['sha256'],67108864)} for which,row in bundle['logdumps'].items()}
    identity=read_json(IDENTITY)
    require(identity.get('product')=='msmnile' and re.fullmatch(r'[A-Za-z0-9._:-]+',identity['serial']),'private identity')
    return {'images':{k:image_hashes(k) for k in IMAGES},'unchanged_boot_sha256':bundle['unchanged_boot_sha256'],
            'private_identity_sha256':sha(IDENTITY),'fastboot_executable_sha256':sha(FASTBOOT),
            'materialization_sha256':sha(MATERIALIZED/'materialization.json'),'activation_pins':pinned_tools()}
''')
operator=operator.replace('pair_hashes','image_hashes').replace("startswith('#363 ')","startswith('#501 ')")
operator=operator.replace("'samurai-image501-fastboot-action-v1'","'samurai-image502-notify-fastboot-action-v1'")
operator=operator.replace("== IMAGES['candidate'][part][2]", "== SIZES[part]")
operator=operator.replace("for part in ('logdump', 'boot'):","for part in ('logdump',):")
operator=operator.replace("result['flashed_pair_sha256']", "result['flashed_images_sha256']").replace("result['pair_complete']", "result['logdump_complete']")
operator=operator.replace("result['partitions_written'] == ['logdump', 'boot'] and result['pair_complete'] is True", "result['partitions_written'] == ['logdump'] and result['logdump_complete'] is True")
operator=operator.replace("result['flashed_pair_sha256']", "result['flashed_images_sha256']")
operator=operator.replace("result['partitions_written'] == ['logdump', 'boot']", "result['partitions_written'] == ['logdump']")
operator=operator.replace("'pair_sha256'", "'images_sha256'")
operator=operator.replace('both exact members successful','only exact logdump successful').replace('Both partition geometries','Read-only partition geometries').replace('two-file operation','logdump-only operation').replace('both partition','read-only partition')
(HERE/'fastboot-operator.py').write_text(operator)

base=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
live=base/'image501-activation/image501-gauge-live-001'
baseline={'adoption':live/'adoption-01-private/adoption-result-private.json',
 'endpoint':live/'adoption-01-private/new-endpoint-private.json',
 'postboot_501':live/'postboot-r1-04-private/stdout-private.json',
 'old501_flash_terminal':live/'fastboot-operator/flash-candidate/result-private.json',
 'old501_reboot_terminal':live/'fastboot-operator/reboot-candidate/result-private.json',
 'camera_wrapper':Path('/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json'),
 'transport':REF/'charging-management-20261023/eud-postboot-transport.py'}
(HERE/'baseline-input-pins.json').write_text(json.dumps({n:{'path':str(p),'sha256':sha(p)} for n,p in baseline.items()},indent=2)+'\n')
provenance={'source_501':PINS,'source_pair_sha256':sha(PAIR/'fastboot-operator.py'),
 'source_generator_sha256':sha(Path(__file__)),'valid_materialized_contract_created':False}
(HERE/'source-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
for n in ['controller.py','remote.py','guard-fragment.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py']:ast.parse((HERE/n).read_text())
print(json.dumps({'source_templates_prepared':True,'valid_prepare_contract_created':False,'device_accessed':False}))
