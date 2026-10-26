from pathlib import Path
import ast,shutil
ref=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel200')
shutil.copyfile(private/'front-overlay-private.dtbo',private/'front-overlay-r1-private.dtbo')
shutil.copyfile(ref/'overlay-build-validation.json',ref/'overlay-build-r1-validation.json')
shutil.copyfile(ref/'capture-front-mmcx-repeat.py',ref/'capture-front-mmcx-r1.py')
overlay=ref/'front-probe-overlay.dtso';s=overlay.read_text()
old='''front_mclk_sleep: samurai-front-mclk-sleep-state {
				pins = "gpio15";
				function = "gpio";
				drive-strength = <2>;
				bias-disable;'''
new=old.replace('bias-disable;', 'bias-pull-down;')
assert old in s;s=s.replace(old,new);overlay.write_text(s)
for name in ['prepare-physical-live-native.py','build-live-overlay.py','capture-front-mmcx-repeat.py']:
 p=ref/name;s=p.read_text().replace('k200-live-prepare-r2','k200-live-prepare-r3')
 if name=='prepare-physical-live-native.py':
  s=s.replace("vio_before=vio_state();assert vio_before==dict(state='unknown',microvolts='1800000',num_users='0')", "vio_before=vio_state();assert vio_before==dict(state='disabled',microvolts='1800000',num_users='0')")
  s=s.replace("read_text())==-22", "read_text())==0").replace('enable_state=-22','enable_state=0')
 if name=='capture-front-mmcx-repeat.py':s=s.replace('k200-front-capture-r1','k200-front-capture-r2')
 ast.parse(s);p.write_text(s)
print('K200_MCLK_SLEEP_PULL_DOWN_AND_FRESH_SECOND_CAPTURE_SESSION_PREPARED')
