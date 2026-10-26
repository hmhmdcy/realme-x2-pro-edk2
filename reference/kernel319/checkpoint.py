from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
assert json.loads((HERE/'resample-build-validation.json').read_text())['passed']
assert json.loads((HERE/'factory-resample-validation.json').read_text())['passed']
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text())
d.update(in_progress_stage=319,in_progress_evidence='../../reference/kernel319/README.md',in_progress_installed=False,
 lsc_mode_resampling_implemented=True,lsc_resampling_host_and_aarch64_verified=True,
 lsc_actual_sensor_mode_mapping_verified=False,lsc_ipa_integration_implemented=False)
p.write_text(json.dumps(d,indent=2)+'\n')
banner='319离线进展：用户空间LSC网格选择与裁剪／binning／翻转重采样已实现，主机和AArch64测试通过；75个原厂表×六组数学映射，397,800浮点值与198,900编码字独立一致。实际传感器采样中心／模式绑定及IPA接入尚未完成，未改手机或包。当前部署仍318。详见reference/kernel319/README.md。本轮工具均终态。\n\n'
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:
 p=ROOT/name;s=p.read_text()
 if not s.startswith('319离线进展：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json']]
for p in paths:
 target=mirror/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
print('Recorded319 offline work; deployed318 unchanged.')
