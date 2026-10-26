"""Integrate the exact deployed camera inputs into the maintained mainline tree."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;U=Path('/home/cy122/x2pro-linux/upstream');P=Path('/mnt/e/edk2-samurai-out/kernel268')
def git(*args):return subprocess.check_output(['git','-C',str(U),*args],text=True).strip()
assert git('rev-parse','HEAD')=='04d4d4f93171574201db1837a1b195e3aeccde4e'
assert not git('status','--porcelain')
assert git('merge-base','HEAD','a90ee4305')=='a90ee4305c4a5df72c11b31dacfdc76e00fcf78a'
out=P/'maintained-source-before-private.json';assert not out.exists()
mapping={
 'drivers/media/i2c/imx319.c':R.parent/'kernel267/imx319.c',
 'drivers/media/i2c/imx319-222mhz-tables.h':R.parent/'kernel267/imx319-222mhz-tables.h',
 'drivers/media/i2c/imx471.c':Path('/mnt/e/edk2-samurai-out/kernel219/timing-source/imx471.c'),
 'drivers/mfd/qcom-pm8008.c':R.parent/'kernel267/qcom-pm8008.c',
 'drivers/regulator/qcom-pm8008-regulator.c':R.parent/'kernel267/qcom-pm8008-regulator.c',
 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts':R.parent/'kernel267/sm8150-samurai.dts',
 'arch/arm64/boot/dts/qcom/imx319.dtsi':R.parent/'kernel267/imx319.dtsi',
 'Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml':R.parent/'kernel267/qcom,pm8008.yaml',
 'Documentation/devicetree/bindings/media/i2c/sony,imx319.yaml':R.parent/'kernel267/sony,imx319.yaml',
}
for name,digest in json.loads((R.parent/'kernel237/camss-source-validation.json').read_text())['candidate_sources'].items():
 p=R.parent/'kernel237/camss-source'/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 mapping['drivers/media/platform/qcom/camss/'+name]=p
# All other CAMSS compilation inputs already match the deployed build's saved tree.
baseline=Path('/mnt/e/edk2-samurai-out/kernel237/camss-build-r1/before/drivers/media/platform/qcom/camss')
for p in baseline.iterdir():
 if p.suffix in ['.c','.h'] and not p.name.endswith('.mod.c'):
  assert (U/'drivers/media/platform/qcom/camss'/p.name).read_bytes()==p.read_bytes()
before={n:hashlib.sha256((U/n).read_bytes()).hexdigest() if (U/n).exists() else None for n in mapping}
out.write_text(json.dumps(before,indent=2)+'\n')
for name,source in mapping.items():shutil.copyfile(source,U/name)
subprocess.run(['git','-C',str(U),'diff','--check'],check=True)
rows={n:hashlib.sha256((U/n).read_bytes()).hexdigest() for n in mapping}
for n,p in mapping.items():assert (U/n).read_bytes()==p.read_bytes()
for n in ['drivers/media/i2c/imx319.c','drivers/mfd/qcom-pm8008.c','drivers/regulator/qcom-pm8008-regulator.c']:
 s=(U/n).read_text();assert not any(x in s for x in ['rmx1931','samurai','imx319_lab'])
report=dict(stage=268,mainline_base='a90ee4305c4a5df72c11b31dacfdc76e00fcf78a',before_head=git('rev-parse','HEAD'),
 source_files_sha256=rows,all_camera_inputs_match_deployed_builds=True,other_camss_sources_match_deployed_build=True,
 existing_kconfig_and_makefile_entries_used=True,no_board_reset_or_lab_module_added=True,git_diff_check_passed=True,
 clean_whole_kernel_build_not_yet_done=True,phone_unchanged=True)
(R/'maintained-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
