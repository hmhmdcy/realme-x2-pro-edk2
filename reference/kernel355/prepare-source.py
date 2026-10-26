from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss');target=source/relative
def git(*a):return subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
base=git('rev-parse','HEAD');assert base=='ea71fa4fd8375502d73231dfb749cbd3a23920eb',base
assert not git('status','--porcelain','--untracked-files=no')
branch='samurai-icp-a5-resources355'
if git('branch','--show-current')!=branch:git('switch','-c',branch)
for f in (HERE/'kernel').iterdir():shutil.copyfile(f,target/f.name)
shutil.copyfile(HERE/'camss-icp-a5-power-test.c',target/'camss-icp-a5-power-test.c')
p=target/'Makefile';s=p.read_text();s+='\nqcom-camss-icp-a5-core-y += camss-icp-a5-resources.o\nobj-$(CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_POWER_TEST) += camss-icp-a5-power-test.o\n';p.write_text(s)
p=target/'Kconfig';s=p.read_text().replace('depends on VIDEO_QCOM_CAMSS && IOMMU_DMA','depends on VIDEO_QCOM_CAMSS && IOMMU_DMA && OF && PM_GENERIC_DOMAINS');s+='\nconfig VIDEO_QCOM_CAMSS_ICP_A5_POWER_TEST\n\ttristate\n\tdepends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && OF_OVERLAY && PM\n';p.write_text(s)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=355,base_commit=base,branch=branch,source_path=str(source),reuses_preceding_checkout=True),indent=2)+'\n')
print(json.dumps(dict(source=str(source),branch=branch,base=base)))
