from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';target=source/'drivers/media/platform/qcom/camss'
def git(*a):return subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
base=git('rev-parse','HEAD');assert base=='0a23a25f34723a9d6fddb3a7c4e94080d0e92b7c',base
assert not git('status','--porcelain','--untracked-files=no')
branch='samurai-icp-a5-bootstrap356'
if git('branch','--show-current')!=branch:git('switch','-c',branch)
for f in (HERE/'kernel').iterdir():shutil.copyfile(f,target/f.name)
shutil.copyfile(HERE/'camss-icp-a5-boot-test.c',target/'camss-icp-a5-boot-test.c')
p=target/'Makefile';p.write_text(p.read_text()+'\nqcom-camss-icp-a5-core-y += camss-icp-a5-boot.o\nobj-$(CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST) += camss-icp-a5-boot-test.o\n')
p=target/'Kconfig';s=p.read_text().replace('&& OF && PM_GENERIC_DOMAINS','&& OF && PM_GENERIC_DOMAINS && RESET_CONTROLLER');s+='\nconfig VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST\n\ttristate\n\tdepends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && OF_OVERLAY\n';p.write_text(s)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=356,parent=base,branch=branch,source=str(source),reuses_preceding_checkout=True),indent=2)+'\n')
print(json.dumps(dict(source=str(source),branch=branch,parent=base)))
