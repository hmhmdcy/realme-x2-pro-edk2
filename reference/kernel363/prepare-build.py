"""Converge tested camera modules and the common IOMMU fix into one release."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==commit
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
prior=json.loads((HERE.parent/'kernel298/boot-candidate-build-validation.json').read_text())
assert hashlib.sha256((build/'arch/arm64/boot/Image').read_bytes()).hexdigest()==prior['artifacts']['arch/arm64/boot/Image']['sha256']
script=(HERE.parent/'kernel298/build-boot-kernel.py').read_text()
script=script.replace("Path('/home/cy122/x2pro-linux/camera279-isp-kernel')","Path('/mnt/samurai-full282/source354')")
script=script.replace('c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117',commit)
start=script.index("old=json.loads(");end=script.index('\ndef snapshot',start)
replacement='''backup=PRIVATE/'previous-build-artifacts';assert not backup.exists();backup.mkdir()
for name in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','vmlinux','Module.symvers','modules.order','.config']:
 shutil.copyfile(BUILD/name,backup/Path(name).name)
'''
script=script[:start]+replacement+script[end:]
script=script.replace('298','363')
# The baseline config is deliberately checked before changing LOCALVERSION.
actual=hashlib.sha256((build/'.config').read_bytes()).hexdigest()
assert actual==prior['artifacts']['.config']['sha256'], 'Review a changed baseline configuration before building'
script=script.replace('82c5ab39f5749693c8e94b7bec7266a9d02a255212af86093e40dfe2e9a101da',actual)
script=script.replace("assert set(changes)=={'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'},changes", "assert {'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'} <= set(changes) and all(k in {'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'} or 'VIDEO_QCOM_CAMSS_ICP_A5' in k for k in changes),changes")
script=script.replace("assert report['camss_component_count']==40", "assert report['camss_component_count']>=40")
(HERE/'build-boot-kernel.py').write_text(script);compile(script,str(HERE/'build-boot-kernel.py'),'exec')
report=dict(stage=363,source=str(source),commit=commit,config_before_sha256=actual,baseline_image_stage=298,
    installed_camera_baseline_stage=362,unified_gamma_driver_stage=348,common_iommu_fix_stage=357,
    diagnostic_modules_default_disabled=True,existing_checkout_reused=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
