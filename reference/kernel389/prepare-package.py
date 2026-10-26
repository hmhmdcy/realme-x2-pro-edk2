"""Record an exact, local deployment bundle; do not change the device."""
from pathlib import Path
import hashlib,json,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;load=lambda n:json.loads((HERE/(n+'-validation.json')).read_text())
for name in ['source','platform','binding','artifact','dt-build','build-package','current-state']:assert load(name)['passed'] if 'passed' in load(name) else load(name)['firmware_build_pass']
build=load('intree-build');boot=load('build-package');mods={r['name']:r for r in build['modules']};release=mods['qcom-camss']['vermagic'].split()[0]
names={'qcom-camss':'drivers/media/platform/qcom/camss','qcom-camss-icp-a5-core':'drivers/media/platform/qcom/camss','camss-icp-a5-m2m':'drivers/media/platform/qcom/camss','v4l2-mem2mem':'drivers/media/v4l2-core','videobuf2-dma-sg':'drivers/media/common/videobuf2'}
files={};modules=[]
for name,directory in names.items():
 row=mods[name];p=Path(row['private_path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 relative='kernel/'+directory+'/'+name+'.ko';archive='modules/'+relative;files[archive]=p
 modules.append(dict(name=name,target_relative=relative,sha256=row['sha256'],bytes=row['bytes'],depends=row['depends']))
firmware=P.parent/'kernel352/CAMERA_ICP.elf-private';digest=hashlib.sha256(firmware.read_bytes()).hexdigest();assert digest=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
files['firmware/camera-icp.elf']=firmware
bootfile=P/'boot-partition-k389-icp-platform.img';rollback=P.parent/'kernel366/boot-partition-k366-icp-dt.img'
assert hashlib.sha256(bootfile.read_bytes()).hexdigest()==boot['boot_sha256'] and hashlib.sha256(rollback.read_bytes()).hexdigest()==boot['rollback_boot_sha256']
files['boot/candidate.img']=bootfile
manifest=dict(stage=389,source_commit=json.loads((HERE/'source-state.json').read_text())['commit'],release=release,modules=modules,
 firmware=dict(target='/lib/firmware/qcom/sm8150/camera-icp.elf',sha256=digest,bytes=firmware.stat().st_size),
 boot=dict(candidate_sha256=boot['boot_sha256'],rollback_sha256=boot['rollback_boot_sha256'],bytes=bootfile.stat().st_size),
 files_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},
 not_uploaded=True,not_installed=True,predeployment_checks_remaining=['Confirm exact current boot/module state and original file presence/absence','Check initramfs for old camera modules','Capture original module files/absence and depmod restoration information','Validate USB/SSH recovery path and rollback boot before transition'],
 current_guard='/var/lib/samurai/k378-recovered/boot-id-private.txt',libcamera_candidate_stage=387,installed_Image363_logdump365_and_user_packages_to_remain=True)
path=P/'deployment-manifest-private.json';path.write_text(json.dumps(manifest,indent=2)+'\n');files['manifest.json']=path
archive=P/'deployment-bundle-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,p in files.items():tar.add(p,arcname=name,recursive=False)
with tarfile.open(archive,'r:gz') as tar:
 assert {m.name for m in tar.getmembers()}==set(files)
 for name,p in files.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(stage=389,modules=len(modules),exact_module_release=release,boot_candidate_sha256=boot['boot_sha256'],rollback_boot366_sha256=boot['rollback_boot_sha256'],firmware_reused_from_original_dump=True,bundle_bytes=archive.stat().st_size,bundle_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),bundle_members_rechecked=True,not_uploaded=True,not_installed=True,predeployment_checks_remaining=manifest['predeployment_checks_remaining'],full_goal_complete=False,passed=True)
(HERE/'deployment-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
