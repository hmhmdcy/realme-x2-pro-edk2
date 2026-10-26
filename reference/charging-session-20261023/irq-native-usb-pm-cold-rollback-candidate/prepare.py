"""Reuse the actual cold disk rollback and current stage rules; offline only."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-oem-audit-20261023/usb-irq-protection-rollback-candidate'
STAGE=HERE.parent/'irq-native-usb-pm-activation-device-candidate'
COHORT=HERE.parent/'irq-native-usb-pm-cohort-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def definitions(path):
 text=path.read_text();tree=ast.parse(text)
 return text,tree,{n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def save(name,value):
 path=HERE/name;assert not path.exists(),name
 path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
 assert sys.argv[1:]==['--prepare'],'explicit source generation only'
 old,tree,functions=definitions(OLD/'restore-worker.py')
 assert sha((OLD/'restore-worker.py').read_bytes())=='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142'
 assert sha((STAGE/'delivery.json').read_bytes())=='69419fee308847a9978b830c396f1919bf227497c60befe3f62b63841e17f7b7'
 assert sha((COHORT/'delivery.json').read_bytes())=='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01'
 stage=(STAGE/'common.py').read_text();assert sha((STAGE/'common.py').read_bytes())=='913cbc5e3aefee784cf9cbac49446dc87c8a985875f9d025e23a076db80f784e'
 package=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01')
 if sys.platform!='win32':package=Path('/mnt/e/'+str(package).replace('\\','/')[3:])
 new_manifest=json.loads((COHORT/'manifest.json').read_bytes());old_manifest_raw=(package/'rollback-manifest.json').read_bytes()
 assert sha(old_manifest_raw)=='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
 inverse=(package/'rollback-7cb-18e8-payload.tar.gz').read_bytes();assert len(inverse)==25858 and sha(inverse)=='6ff66d182f7b0dc7ac32e3e58ae756e259c246b4edddf85d48878ff561835ab8'
 release=new_manifest['release'];usb=new_manifest['modules']['samurai-usb-input']['target'];manifest='/usr/share/samurai-charging/manifest.json'
 notes={'samurai-usb-input':'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d',
  'samurai-gauge-protection':'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',
  'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
 constants=dict(OLD_FILES={usb:'7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f',manifest:sha(old_manifest_raw)},
  NEW_FILES={usb:new_manifest['modules']['samurai-usb-input']['sha256'],manifest:sha((COHORT/'manifest.json').read_bytes())},
  OLD_NOTES=notes,NEW_NOTES={**notes,'samurai-usb-input':'08523f9f969b00a278a87ddd5d27ec3b54ac9b53a9c84f6429c4ecf5934c0f3f'},NEW_MANIFEST=new_manifest,
  RELEASE=release,VERSION502='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',VERSION504='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',
  BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06',
  LOGDUMP502='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
  LOGDUMP504='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83',
  ROOT='/root/charging-management-20261023',SERVICE='/usr/sbin/samurai-charging',
  MANAGER='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4',
  LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b',
  STARTUP_SHA='2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a',
  LOCK='/run/lock/samurai-charging.lock',INSTANCE='/sys/devices/platform/samurai-gauge-protection',
  MANIFEST=manifest,USB=usb,ORDER=[usb,manifest],ROLLBACK_PAYLOAD=sha(inverse),
  STAGE_WORKER='8e188610e8002c4d23a70a7d3d01572366ebf668c0674ac93ea4f05b23aeb7e8',
  STAGE_SUPERVISOR='b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc',STAGE_RULES=stage,STAGE_RULES_SHA=sha(stage.encode()))
 source='''"""Default inert. Exact two-file cold rollback; no module/carrier activation."""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import argparse,base64,copy,hashlib,io,json,math,os,re,runpy,stat,struct,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
'''
 source+='\n'.join(name+'='+repr(value) for name,value in constants.items())+'\n\n'
 exact=['need','sha','detail','encode','read_owned','AtomicFailure','validate_lease','atomic_replace','active','safe_electrical','safe_stopped','idle']
 for name in exact:source+=functions[name]+'\n\n'
 source+=functions['retained'].replace('def retained(','def legacy_retained(',1)+'\n\n'
 source+=functions['restore'].replace('samurai-usb-irq-protection-rollback-result-v1','samurai-irq-native-usb-pm-cold-rollback-result-v1').replace("expected_profile(request)[1]","expected_profile(request)['notes']")+'\n\n'
 device=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Device')
 methods=[];source+='class BaseDevice:\n'
 for node in device.body:
  if isinstance(node,ast.FunctionDef) and node.name not in ['identity','source_proof']:
   methods.append(node.name);source+='    '+ast.get_source_segment(old,node)+'\n\n'
 source+=(HERE/'current-body.py.inc').read_text()+'\n\n'+functions['main']+"\n\nif __name__=='__main__':raise SystemExit(main())\n"
 compile(source,'restore-worker.py','exec')
 path=HERE/'restore-worker.py';assert not path.exists();path.write_text(source,encoding='utf-8',newline='\n')
 save('source-reuse.json',dict(passed=True,original_worker_sha256=sha((OLD/'restore-worker.py').read_bytes()),
  original_stage_common_sha256=sha((STAGE/'common.py').read_bytes()),exact_functions=exact,
  original_retained_body_reused_under_name='legacy_retained',restore_changes='result schema and named profile notes only',
  exact_base_device_methods=methods,embedded_stage_rules_exact=True,device_accessed=False))
 save('contract.json',dict(schema='samurai-irq-native-usb-pm-cold-rollback-contract-v1',request_schema='samurai-irq-native-usb-pm-cold-rollback-request-v1',
  profiles=['staged_same_boot_old_resident','booted_504_new_resident','booted_502_new_resident'],
  worker_sha256=sha(path.read_bytes()),payload_sha256=sha(inverse),payload_bytes=len(inverse),
  source_stage_evidence_count=17,current_cache_from_fresh_original_key_probe_required=True,
  whole_postboot_success_not_required=True,write_scope=[usb,manifest],
  source_profile='exact502/bootedd/ace2/7cb/97c/7848/18e8',new_profile='exact504/bootedd/4453/d046/97c/7848/34ead',
  original_carrier_new_modules_profile='exact502/bootedd/ace2/d046/97c/7848/34ead',
  success='staged_original/runtime_pending',module_or_carrier_actions=False,
  complete_recovery_requires_old_disk_and_logdump_ace2_then_normal_restart=True,actual_runtime_request_created=False))
 print(json.dumps({'prepared':True,'worker_sha256':sha(path.read_bytes()),'exact_functions':len(exact),'exact_base_methods':len(methods),'device_accessed':False}))
if __name__=='__main__':main()
