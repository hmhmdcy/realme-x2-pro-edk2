"""Bind existing Image504 FAT/rollback and current workers. Offline only."""
from pathlib import Path
import argparse,ast,hashlib,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'irq-native-usb-pm-materialized-001'
FAT=REF/'charging-oem-audit-20261023/image504-budget-logdump-candidate'
COHORT=HERE.parent/'irq-native-usb-pm-cohort-candidate'
OLD_BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
OLD_FAT='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
NEW_FAT='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83'
NEW_IMAGE='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'
SOURCE_NAMES=['common.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py','stage-proof.py','stage-source-pins.json',
 'prepare-contract.json','materialize.py','test-delta.py','test-result.json']
def sha(path):
 p=Path(path);assert p.is_file() and not p.is_symlink(),p
 digest=hashlib.sha256()
 with p.open('rb') as stream:
  while data:=stream.read(1048576):digest.update(data)
 return digest.hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def local(path):
 value=str(path).replace('\\','/')
 return Path('/mnt/'+value[0].lower()+value[2:] if os.name!='nt' and len(value)>2 and value[1:3]==':/' else value)
def checked(path,digest,size=None):
 p=local(path);assert size is None or p.stat().st_size==size,p
 assert sha(p)==digest,p;return p
def pinned_fat_proof(verify_binaries=False):
 c=load(COHORT/'delivery.json');assert sha(COHORT/'delivery.json')=='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01' and c['passed']
 checked(COHORT/'cohort-manifest.json',c['files']['cohort-manifest.json']['sha256'])
 cohort=load(COHORT/'cohort-manifest.json');inputs=cohort['input_files']
 delivery=load(FAT/'delivery.json');report=load(FAT/'logdump-result.json');execution=load(FAT/'execution-receipt.json')
 assert sha(FAT/'delivery.json')=='4351a49e4de397f0de0f0504645f71d0abdbcab41053b1a63c620df759f87822'
 assert sha(FAT/'logdump-result.json')==inputs['carrier_receipt']['sha256']
 for name in ['logdump-result.json','execution-receipt.json']:
  checked(FAT/name,delivery['files'][name]['sha256'])
 assert delivery['passed'] and report['passed'] and execution['original_exec_terminal'] and execution['original_exec_exit_code']==0
 assert execution['same_original_handle_observed_through_exit'] and execution['timeout_kill_or_replay'] is False
 assert [x['stage'] for x in execution['original_tools']]==['replace-Image','readback-Image','fsck-readonly']
 assert all(x['terminal'] and type(x['returncode']) is int and x['returncode']==0 and x['pid']>0 for x in execution['original_tools'])
 for name in ['only_Image_file_changed','other_entries_and_contents_exact','all_non_Image_bytes_exact','Image_readback_exact','fsck_readonly_passed',
  'native_DTB_untouched','rootfs_R8_camera_untouched','no_device_or_deployment','parent_inputs_unchanged','parent_mountinfo_unchanged']:assert report[name] is True,name
 assert report['logdump_sha256']==NEW_FAT and report['rollback_logdump_sha256']==OLD_FAT and report['Image504_sha256']==NEW_IMAGE
 assert delivery['candidate']['sha256']==NEW_FAT and delivery['rollback']['sha256']==OLD_FAT and delivery['Image504']['sha256']==NEW_IMAGE
 assert cohort['unchanged_boot']=={'sha256':OLD_BOOT,'bytes':100663296} and cohort['required_logdump']=={'sha256':NEW_FAT,'bytes':67108864}
 rows={'candidate':inputs['carrier:forward_logdump'],'original':inputs['carrier:rollback_logdump']}
 for which,row in rows.items():
  assert row['sha256']==(NEW_FAT if which=='candidate' else OLD_FAT) and row['bytes']==67108864
  if verify_binaries:checked(row['path'],row['sha256'],row['bytes'])
 boot=inputs['carrier:boot'];assert boot['sha256']==OLD_BOOT and boot['bytes']==100663296
 if verify_binaries:checked(boot['path'],OLD_BOOT,100663296)
 # The older FAT author's unchanged_boot field describes its saved 97811 source;
 # current IRQ bootedd comes from the current cohort, not that historical field.
 return {'fat_delivery_sha256':sha(FAT/'delivery.json'),'fat_report_sha256':sha(FAT/'logdump-result.json'),
  'fat_execution_sha256':sha(FAT/'execution-receipt.json'),'cohort_delivery_sha256':sha(COHORT/'delivery.json'),
  'logdumps':{k:{'path':str(local(v['path'])),'sha256':v['sha256']} for k,v in rows.items()},
  'unchanged_boot_sha256':OLD_BOOT,'unchanged_boot_path':str(local(boot['path'])),'Image504_sha256':NEW_IMAGE}
def source_inputs():
 for name in SOURCE_NAMES:
  ast.parse((HERE/name).read_text()) if name.endswith('.py') else load(HERE/name)
 tested=load(HERE/'test-result.json');assert tested['passed']
 for name,digest in tested['tested_files'].items():assert sha(HERE/name)==digest,name
 return {name:sha(HERE/name) for name in SOURCE_NAMES}
def create(path,raw):
 with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
def save(path,value):create(path,(json.dumps(value,indent=2)+'\n').encode())
def materialize():
 assert not OUT.exists(),'existing materialized bundle must not be overwritten'
 proof=pinned_fat_proof(True);sources=source_inputs();contract=load(HERE/'prepare-contract.json')
 assert contract['write_scope']==contract['fixed_guard_fields']['partitions']==['logdump'] and contract['boot_is_readonly_invariant']
 assert contract['fixed_guard_fields']['unchanged_boot_sha256']==OLD_BOOT and contract['fixed_guard_fields']['candidate_logdump_sha256']==NEW_FAT
 workers={name:(HERE/name).read_bytes() for name in ['eud-quiesce.py','eud-restart.py']}
 OUT.mkdir(mode=0o700)
 for name,data in workers.items():create(OUT/name,data)
 save(OUT/'prepare-contract.json',contract)
 save(OUT/'activation-pins.json',{n:sha(OUT/n) for n in ['prepare-contract.json','eud-restart.py']})
 receipt={'schema':'samurai-irq-native-usb-pm-materialization-v1','passed':True,'source_files':sources,**proof,
  'files':{n:sha(OUT/n) for n in [*workers,'prepare-contract.json','activation-pins.json']},
  'worker_hashes':{n:sha(OUT/n) for n in workers},'no_device_action_performed':True}
 save(OUT/'materialization.json',receipt)
 fd=os.open(OUT,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return validate_bundle(OUT)
def validate_bundle(out=OUT):
 out=Path(out);r=load(out/'materialization.json')
 assert r['schema']=='samurai-irq-native-usb-pm-materialization-v1' and r['passed'] and r['source_files']==source_inputs()
 proof=pinned_fat_proof(False);assert all(r[k]==v for k,v in proof.items())
 for name,digest in r['files'].items():checked(out/name,digest)
 assert r['worker_hashes']=={n:sha(out/n) for n in ['eud-quiesce.py','eud-restart.py']}
 contract=load(out/'prepare-contract.json');assert contract==load(HERE/'prepare-contract.json')
 return r
def check_local():
 for name in ['common.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py','stage-proof.py']:ast.parse((HERE/name).read_text())
 return {'source_only':True,'device_accessed':False,'materialized_bundle_created':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--materialize',action='store_true');a=p.parse_args()
 if a.materialize:
  result=materialize();print(json.dumps({'passed':result['passed'],'device_accessed':False,'runtime_identity_created':False,'materialized_path':str(OUT)}))
 else:print(json.dumps(check_local()))
