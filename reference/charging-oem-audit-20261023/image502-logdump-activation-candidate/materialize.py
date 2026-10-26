"""Local-only source/payload binding. No valid contract until frozen FAT proof passes."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,os,sys
if sys.flags.optimize:raise RuntimeError('optimized interpreter is unsupported')
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'image502-notify-materialized-001'
FAT=REF/'charging-session-20261023/gauge-image502-logdump-candidate'
IMAGE_LEAF=REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
OLD_BOOT='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
OLD_FAT='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
NEW_IMAGE='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
NEW_FAT='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
SOURCE_NAMES=['controller.py','remote.py','guard-fragment.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py','materialize.py','baseline-input-pins.json','fat-input-pin.json','test-result.json','test-delta.py']
def sha(p):
 p=Path(p);assert p.is_file() and not p.is_symlink(),p
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def checked(p,digest,size=None):
 p=Path(p);assert size is None or p.stat().st_size==size,p
 assert sha(p)==digest,p;return p
def pinned_fat_proof():
 pin=load(HERE/'fat-input-pin.json');assert pin['ready'] is True
 checked(FAT/'delivery.json',pin['delivery_sha256'])
 checked(FAT/'logdump-result.json',pin['logdump_result_sha256'])
 delivery=load(FAT/'delivery.json');report=load(FAT/'logdump-result.json')
 assert delivery['passed'] and report['passed']
 assert delivery['files']['logdump-result.json']==pin['logdump_result_sha256']
 assert delivery['candidate']['sha256']==NEW_FAT and delivery['candidate']['bytes']==67108864 and delivery['rollback']['sha256']==OLD_FAT
 assert delivery['unchanged_boot_sha256']==OLD_BOOT and delivery['Image502']['sha256']==NEW_IMAGE
 for k in ['only_Image_file_changed','other_entries_and_contents_exact','all_non_Image_bytes_exact','Image_readback_exact','fsck_readonly_passed','native_DTB_untouched','rootfs_R8_camera_untouched','no_device_or_deployment','parent_inputs_unchanged','parent_mountinfo_unchanged']:assert report[k] is True,k
 assert report['rollback_logdump_sha256']==OLD_FAT and report['Image502_sha256']==NEW_IMAGE
 assert report['logdump_sha256']==NEW_FAT and report['logdump_bytes']==67108864
 private_result=PRIVATE/'gauge-image502-logdump-private-01/result.json'
 checked(private_result,report['private_result_sha256']);raw=load(private_result)
 assert raw['passed'] and raw['parent_inputs_unchanged'] and raw['inputs_before']==raw['inputs_after']
 assert raw['logdump_sha256']==NEW_FAT and raw['rollback_logdump_sha256']==OLD_FAT and raw['Image502_sha256']==NEW_IMAGE
 assert [c['stage'] for c in raw['commands']]==['replace-Image','readback-Image','fsck-readonly'] and all(c['returncode']==0 for c in raw['commands'])
 checked(IMAGE_LEAF/'delivery.json','4e27a8da005b3e5b41799f63a9a3b3e4de1b22f6d60f8a1172c2c28cd8163e21')
 imdelivery=load(IMAGE_LEAF/'delivery.json');assert imdelivery['passed']
 assert imdelivery['outputs']['arch/arm64/boot/Image']=={'bytes':59243008,'sha256':NEW_IMAGE}
 old=checked(PRIVATE/'gauge-image501-logdump-private-01/logdump-gauge501-private.img',OLD_FAT,67108864)
 new=checked(PRIVATE/'gauge-image502-logdump-private-01/logdump-gauge502-private.img',NEW_FAT,67108864)
 assert report['logdump_path']==str(new)
 image=checked('/home/cy122/charging-management-20261023/gauge-image502-notify-01/build/arch/arm64/boot/Image',NEW_IMAGE,59243008)
 boot=checked(PRIVATE/'gauge-image501-boot-private-01/boot-gauge501-private.img',OLD_BOOT,100663296)
 return {'fat_delivery_sha256':sha(FAT/'delivery.json'),'fat_report_sha256':sha(FAT/'logdump-result.json'),
  'fat_private_result_sha256':sha(private_result),'image_delivery_sha256':sha(IMAGE_LEAF/'delivery.json'),
  'logdumps':{'candidate':{'path':str(new),'sha256':NEW_FAT},'original':{'path':str(old),'sha256':OLD_FAT}},
  'unchanged_boot_sha256':OLD_BOOT,'unchanged_boot_path':str(boot),'Image502_sha256':NEW_IMAGE,'Image502_path':str(image)}
def source_inputs():
 for name in SOURCE_NAMES:ast.parse((HERE/name).read_text()) if name.endswith('.py') else load(HERE/name)
 tested=load(HERE/'test-result.json');assert tested['passed']
 for name,digest in tested['tested_files'].items():assert sha(HERE/name)==digest,name
 return {name:sha(HERE/name) for name in SOURCE_NAMES}
def create(p,raw):
 with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def save(p,value):create(p,(json.dumps(value,indent=2)+'\n').encode())
def materialize():
 assert not OUT.exists(),'materialization directory consumed; never overwrite/replay'
 proof=pinned_fat_proof();sources=source_inputs()
 spec=importlib.util.spec_from_file_location('image502_profile_only',HERE/'controller.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 pins=load(HERE/'baseline-input-pins.json');raw={n:checked(p['path'],p['sha256']).read_bytes() for n,p in pins.items()}
 m.profile(raw)
 fixed={'schema':'samurai-image502-notify-activation-v1','unchanged_boot_sha256':OLD_BOOT,'boot_bytes':100663296,
  'candidate_logdump_sha256':NEW_FAT,'rollback_logdump_sha256':OLD_FAT,'logdump_bytes':67108864,'partitions':['logdump'],
  'kernel_release':'7.3.0-rc6-rmx1931-samurai-k363+','image501_sha256':'3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02','image502_sha256':NEW_IMAGE,
  'old_boot_guard_path':'/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt',
  'camera481_expected_sha256':'1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705',
  'charging_manifest_sha256':'320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f',
  'startup500_sha256':'2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a','startup500_path':'/usr/local/sbin/samurai-usb','max_power_ma':500}
 contract={'schema':fixed['schema'],'transaction_id':'image502-notify-live-001','fixed_guard_fields':fixed,
  'write_scope':['logdump'],'boot_is_readonly_invariant':True,'rollback_logdump_sha256':OLD_FAT,
  'source_and_payload_proof':proof,'current_scene_condition':'root verifies present assistance availability; ordinary repair/restart authorization persists',
  'no_device_action_performed':True}
 workers={}
 for name in ['guard-fragment.py','eud-quiesce.py','eud-restart.py']:
  text=(HERE/name).read_text();assert text.count('__MATERIALIZE_LOGDUMP_SHA256__')==1
  workers[name]=text.replace('__MATERIALIZE_LOGDUMP_SHA256__',NEW_FAT).encode();ast.parse(workers[name])
 OUT.mkdir(mode=0o700)
 for name,data in workers.items():create(OUT/name,data)
 save(OUT/'prepare-contract.json',contract)
 save(OUT/'activation-pins.json',{n:sha(OUT/n) for n in ['prepare-contract.json','eud-restart.py']})
 receipt={'schema':'samurai-image502-notify-materialization-v1','passed':True,'source_files':sources,**proof,
  'files':{n:sha(OUT/n) for n in [*workers,'prepare-contract.json','activation-pins.json']},
  'worker_hashes':{n:sha(OUT/n) for n in ['eud-quiesce.py','eud-restart.py']},'no_device_action_performed':True}
 save(OUT/'materialization.json',receipt)
 fd=os.open(OUT,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return validate_bundle(OUT)
def validate_bundle(out=OUT):
 out=Path(out);r=load(out/'materialization.json')
 assert r['schema']=='samurai-image502-notify-materialization-v1' and r['passed']
 assert r['source_files']==source_inputs()
 proof=pinned_fat_proof()
 assert all(r[k]==v for k,v in proof.items())
 for n,digest in r['files'].items():checked(out/n,digest)
 assert r['worker_hashes']=={n:sha(out/n) for n in ['eud-quiesce.py','eud-restart.py']}
 c=load(out/'prepare-contract.json');assert c['write_scope']==c['fixed_guard_fields']['partitions']==['logdump']
 assert c['boot_is_readonly_invariant'] and c['fixed_guard_fields']['unchanged_boot_sha256']==OLD_BOOT
 assert c['fixed_guard_fields']['rollback_logdump_sha256']==OLD_FAT and c['fixed_guard_fields']['candidate_logdump_sha256']==NEW_FAT
 return r
def check_local():
 source={}
 for n in ['controller.py','remote.py','guard-fragment.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py']:ast.parse((HERE/n).read_text());source[n]=sha(HERE/n)
 if not OUT.exists():return {'checked_sources':True,'source_sha256':source,'materialized_ready':False,'device_accessed':False}
 r=validate_bundle();return {'checked_sources':True,'materialized_ready':True,'materialization_sha256':sha(OUT/'materialization.json'),'logdumps':r['logdumps'],'device_accessed':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--materialize',action='store_true');a=p.parse_args()
 r=materialize() if a.materialize else check_local()
 print(json.dumps(r,indent=2))
