"""Derive current cold-stage guards and logdump-only operator. Offline only."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=HERE.parent/'usb-irq-protection-restart-candidate'
LOG=REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate'
STAGE=REF/'charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate'
COHORT=HERE.parent/'irq-native-usb-pm-cohort-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def definitions(path):
 source=path.read_text();tree=ast.parse(source)
 return source,{n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
def replace_function(source,name,new):
 tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 lines=source.splitlines(True);return ''.join(lines[:node.lineno-1])+new+'\n\n'+''.join(lines[node.end_lineno:])
def write(path,raw):
 assert path.parent==HERE and not (HERE/'delivery.json').exists(),'only regenerate this unfrozen source leaf'
 path.write_bytes(raw if isinstance(raw,bytes) else raw.encode())
def saved(path,value):write(path,json.dumps(value,indent=2)+'\n')
def main():
 assert sys.argv[1:]==['--prepare'],'explicit offline generation only'
 assert not (HERE/'delivery.json').exists(),'frozen sources are not regenerated'
 assert sha((STAGE/'delivery.json').read_bytes())=='01988b4c02aacf6a53a83863bb9fac3ce25695f6342c941db4674cf6859b4132'
 assert sha((COHORT/'delivery.json').read_bytes())=='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01'
 for leaf in [OLD,LOG,STAGE,COHORT]:
  delivery=json.loads((leaf/'delivery.json').read_bytes());assert delivery['passed'] and delivery['frozen']
  for name,row in delivery['files'].items():assert sha((leaf/name).read_bytes())==(row['sha256'] if isinstance(row,dict) else row)
 old,functions=definitions(OLD/'common.py');_,changes=definitions(HERE/'current-gates.py.inc')
 fixed=json.loads((OLD/'prepare-contract.json').read_bytes())['fixed_guard_fields']
 for key in ['candidate_boot_sha256','rollback_boot_sha256','unchanged_logdump_sha256']:fixed.pop(key)
 fixed.update(schema='samurai-irq-native-usb-pm-activation-v1',kernel_version='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',
  source_kernel_version='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',partitions=['logdump'],
  unchanged_boot_sha256='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06',
  candidate_logdump_sha256='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83',
  rollback_logdump_sha256='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
  image504_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4',
  charging_manifest_sha256='34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b',
  source_manifest_sha256='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5',
  cohort_delivery_sha256='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01')
 manifest=json.loads((COHORT/'manifest.json').read_bytes())
 usb=manifest['modules']['samurai-usb-input']['target'];mpath='/usr/share/samurai-charging/manifest.json'
 notes={'samurai-usb-input':'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d',
  'samurai-gauge-protection':'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',
  'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
 fixed['old_resident_notes']={k.replace('-','_'):v for k,v in notes.items()}
 fixed['new_disk_files']={usb:manifest['modules']['samurai-usb-input']['sha256'],mpath:fixed['charging_manifest_sha256']}
 oldraw=(Path('/mnt/e/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01/rollback-manifest.json')
  if sys.platform!='win32' else Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01/rollback-manifest.json')).read_bytes()
 assert sha(oldraw)==fixed['source_manifest_sha256']
 oldtree=ast.parse(old);constants={}
 for node in oldtree.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
   name=node.targets[0].id
   if name in ['CAMERA481','SENSOR468_NOTE']:constants[name]=ast.literal_eval(node.value)
 constants.update(FIXED=fixed,EXPECTED_MANIFEST=manifest,OLD_MANIFEST=json.loads(oldraw),
  RELEASE=manifest['release'],VERSION=fixed['source_kernel_version'],BOOT=fixed['unchanged_boot_sha256'],
  LOGDUMP=fixed['rollback_logdump_sha256'],OLD=fixed['source_manifest_sha256'],OLD_NOTES=notes,
  USB=usb,MANIFEST=mpath,OLD_FILES={usb:'7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f',mpath:fixed['source_manifest_sha256']},
  PAYLOAD='f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc',
  MAC_CACHE_SHA='02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8')
 source='''"""Current cold-stage guards. Definitions have no device side effects."""
import base64,fcntl,hashlib,json,os,re,runpy,stat,struct,sys,time,uuid
from pathlib import Path
ROOT=Path('/root/charging-management-20261023')
SERVICE_LOCK='/run/lock/samurai-charging.lock'
STAGE_WORKER='8e188610e8002c4d23a70a7d3d01572366ebf668c0674ac93ea4f05b23aeb7e8'
STAGE_SUPERVISOR='b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'
LIVE_PATH='/usr/lib/samurai-charging/live-session.py'
LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
_SERVICE_FD=None
_MAC_FD=None
'''
 source+='\n'.join(k+'='+repr(v) for k,v in constants.items())+'\n\n'
 excluded={'validate_adoption','validate_activation_guard'}|set(changes)
 exact=[]
 for name,body in functions.items():
  if name not in excluded:source+=body+'\n\n';exact.append(name)
 source+=(HERE/'current-gates.py.inc').read_text()+'\n\n'
 guard=functions['validate_activation_guard']
 begin=guard.index(" adoption=meta['adoption'];");end=guard.index(' records=read_stage(meta)',begin)
 guard=guard[:begin]+''' adoption=meta['adoption'];need(set(adoption)=={'transaction_id','guard_path','guard_sha256'},'actual IRQ adoption fields')
 need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',adoption['transaction_id']) and
  adoption['guard_path']=='/var/lib/samurai/'+adoption['transaction_id']+'-adopted/boot-id-private.txt' and
  re.fullmatch('[0-9a-f]{64}',adoption['guard_sha256']),'actual source IRQ adopted guard')
 owned_directory(Path(adoption['guard_path']).parent)
 guard=raw_owned(adoption['guard_path']);need(guard==(meta['boot_id']+'\\n').encode() and sha(guard)==adoption['guard_sha256'],'actual adopted guard bytes')
'''+guard[end:]
 guard=guard.replace("os.uname().version==FIXED['kernel_version']","os.uname().version==FIXED['source_kernel_version']")
 guard=guard.replace("FIXED['rollback_boot_sha256']","FIXED['unchanged_boot_sha256']").replace("FIXED['unchanged_logdump_sha256']","FIXED['rollback_logdump_sha256']")
 guard=guard.replace('three actual new disk files','two actual new disk files')
 guard=guard.replace(' data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))',
  " verify_consumed_cache(records['after']['mac_evidence'])\n data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))\n verify_consumed_cache(records['after']['mac_evidence'])")
 source+=guard+'\n';compile(source,'common.py','exec');write(HERE/'common.py',source)
 suffixes=[]
 for name in ['eud-quiesce.py','eud-restart.py']:
  original=(OLD/name).read_text();header=original[:original.index('"""Stage-aware device gates.')]
  suffix=original[original.index('assert len(sys.argv)==4'):].replace("work='usb-irq-protection-activation'","work='irq-native-usb-pm-activation'")
  new=header+source+'\n'+suffix;compile(new,name,'exec');write(HERE/name,new)
  suffixes.append(dict(name=name,original_sha256=sha((OLD/name).read_bytes()),candidate_sha256=sha(new.encode()),
   normalized_original_suffix_equal=suffix.replace("work='irq-native-usb-pm-activation'","work='usb-irq-protection-activation'")==original[original.index('assert len(sys.argv)==4'):]))
 contract=dict(schema=fixed['schema'],fixed_guard_fields=fixed,transaction_pattern='irq-native-usb-pm-activate-[a-z0-9-]{8,48}',
  write_scope=['logdump'],boot_is_readonly_invariant=True,dynamic_guard_fields=['transaction_id','token','boot_id','soc_serial_sha256','compatible_sha256','rootfs_release_sha256','adoption','stage'],
  adoption_fields=['transaction_id','guard_path','guard_sha256'],stage_fields=['transaction_id','request_sha256','result_sha256','host_binding_sha256','worker_sha256','supervisor_sha256','evidence'],
  stage_evidence_keys=list(__import__('re').findall("'([a-z_]+)'\\s*:",changes['stage_paths'])),
  context_schema='samurai-irq-native-usb-pm-fastboot-context-v1',host_source_authentication_required=True,
  host_source='current stage-host binding of original IRQ adoption plus completed 97c runtime update',
  new_boot_identity_generated=False,no_device_action_performed=True)
 saved(HERE/'prepare-contract.json',contract)
 saved(HERE/'source-reuse.json',dict(passed=True,exact_common_functions=exact,worker_suffixes=suffixes,
  sources={str(p.relative_to(REF)):sha(p.read_bytes()) for p in [OLD/'delivery.json',OLD/'common.py',LOG/'delivery.json',STAGE/'delivery.json',COHORT/'delivery.json']},
  actual_runtime_identity_or_guard_created=False,device_accessed=False))
 print(json.dumps(dict(prepared=True,exact_common_functions=len(exact),suffixes_preserved=all(x['normalized_original_suffix_equal'] for x in suffixes),device_accessed=False)))
if __name__=='__main__':main()
