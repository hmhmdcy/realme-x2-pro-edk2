"""Expose native S5K3M5 gain codes and pair them with a public libcamera helper."""
from pathlib import Path
import difflib, hashlib, json, shutil, subprocess
import host

R = Path(__file__).resolve().parent
K = Path('/home/cy122/x2pro-linux/camera270-kernel')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=K,text=True).strip() == 'edd2e8c14a760b8a889b9313f45acfc1d015a7fb'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=K)
subprocess.run(['git','switch','-c','samurai-camera-gain271'],cwd=K,check=True,capture_output=True)
p = K / 'drivers/media/i2c/s5k3m5.c'
old = p.read_text()
assert hashlib.sha256(old.encode()).hexdigest() == json.loads((R.parent/'kernel270/telephoto-source-validation.json').read_text())['source_sha256']
new = old
for a,b in [('#define S5K3M5_AGAIN_MIN\t\t1', '#define S5K3M5_AGAIN_MIN\t\t32'),
            ('#define S5K3M5_AGAIN_MAX\t\t16', '#define S5K3M5_AGAIN_MAX\t\t512'),
            ('#define S5K3M5_AGAIN_DEFAULT\t\t1', '#define S5K3M5_AGAIN_DEFAULT\t\t32'),
            ('#define S5K3M5_AGAIN_SHIFT\t\t5\n', ''),
            ('ctrl->val << S5K3M5_AGAIN_SHIFT', 'ctrl->val')]:
    assert new.count(a) == 1, a
    new = new.replace(a,b)
p.write_text(new)
(R/'s5k3m5.c').write_text(new)
shutil.copyfile(K/'drivers/media/i2c/s5k3m5-19mhz-tables.h',R/'s5k3m5-19mhz-tables.h')
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/media/i2c/s5k3m5.c',tofile='b/drivers/media/i2c/s5k3m5.c'))
(R/'s5k3m5-native-gain-code.patch').write_text(patch)
sdk = Path('/home/cy122/x2pro-linux/libcamera214-root')
source = sdk/'work/libcamera268-r19-built/src/libcamera-v0.7.2/src/ipa/libipa/camera_sensor_helper.cpp'
before = source.read_text()
needle='class CameraSensorHelperImx319 : public CameraSensorHelper'
assert before.count(needle)==1 and 'REGISTER_CAMERA_SENSOR_HELPER("s5k3m5"' not in before
helper='''class CameraSensorHelperS5k3m5 : public CameraSensorHelper
{
public:
	CameraSensorHelperS5k3m5()
	{
		/* Native sensor code: 0x20 is 1x, 0x200 is 16x. */
		gain_ = AnalogueGainLinear{ 1, 0, 0, 32 };
	}
};
REGISTER_CAMERA_SENSOR_HELPER("s5k3m5", CameraSensorHelperS5k3m5)

'''
after=before.replace(needle,helper+needle)
helper_patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/src/ipa/libipa/camera_sensor_helper.cpp',tofile='b/src/ipa/libipa/camera_sensor_helper.cpp'))
name='0024-s5k3m5-native-gain-helper.patch'
recipe=R/'recipes/libcamera';recipe.mkdir(parents=True)
base=R.parents[1]/'linux-port/packages/libcamera'
for p in base.iterdir():
    if p.is_file() and p.name not in ['source-lock.json','README.md']:shutil.copyfile(p,recipe/p.name)
(recipe/name).write_text(helper_patch);(R/name).write_text(helper_patch)
apk=(recipe/'APKBUILD').read_text()
assert 'pkgrel=19' in apk
apk=apk.replace('pkgrel=19','pkgrel=20').replace('\t0023-simple-link-state-after-external-client.patch\n','\t0023-simple-link-state-after-external-client.patch\n\t'+name+'\n')
suffix=apk.rfind('"')
apk=apk[:suffix]+hashlib.sha512(helper_patch.encode()).hexdigest()+'  '+name+'\n'+apk[suffix:]
(recipe/'APKBUILD').write_text(apk)
config=R/'recipes/samurai-camera-config';config.mkdir()
for p in (R.parents[1]/'linux-port/packages/samurai-camera-config').iterdir():
    if p.is_file() and p.name not in ['source-lock.json','README.md']:shutil.copyfile(p,config/p.name)
p=config/'APKBUILD';s=p.read_text();assert 'pkgrel=14' in s
p.write_text(s.replace('pkgrel=14','pkgrel=15').replace('99990.7.2-r19','99990.7.2-r20'))
for src,dest in [(recipe,sdk/'work/libcamera271-r20'),(config,sdk/'work/samurai-camera-config271-r20')]:
    assert not dest.exists();shutil.copytree(src,dest)
report=dict(stage=271,branch='samurai-camera-gain271',parent='edd2e8c14a760b8a889b9313f45acfc1d015a7fb',
 kernel_source_before_sha256=hashlib.sha256(old.encode()).hexdigest(),kernel_source_sha256=hashlib.sha256(new.encode()).hexdigest(),
 source_before_files={'src/ipa/libipa/camera_sensor_helper.cpp':hashlib.sha256(before.encode()).hexdigest()},
 source_files={'src/ipa/libipa/camera_sensor_helper.cpp':hashlib.sha256(after.encode()).hexdigest()},patch_count=24,
 gain_codes=[32,512],real_gains=[1,16],gain_step=1/32,voltage_gpio_clock_mode_tables_unchanged=True,
 black_level_not_assumed=True,existing_sensors_helpers_unchanged=True,phone_not_modified=True)
(R/'gain-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
