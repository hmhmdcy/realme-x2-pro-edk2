"""Retain the tested sensor-only change while preserving the complete #298 baseline."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'geometry-install-validation.json').read_text())['passed']
assert json.loads((HERE/'four-camera-regression-validation.json').read_text())['passed']
assert json.loads((HERE/'interrupt-restoration-validation.json').read_text())['passed']
assert json.loads((HERE/'final-health-validation.json').read_text())['checked_camera_runtime_healthy']
tree=Path('/home/cy122/x2pro-linux/camera305-sensor-kernel')
base=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
assert subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],text=True).strip()=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117'
assert not subprocess.check_output(['git','-C',str(base),'status','--porcelain'])
assert subprocess.check_output(['git','-C',str(tree),'diff','--name-only'],text=True).splitlines()==['drivers/media/i2c/s5k3m5.c']
expected=json.loads((HERE/'kernel-build-validation.json').read_text())
assert hashlib.sha256((tree/'drivers/media/i2c/s5k3m5.c').read_bytes()).hexdigest()==expected['source_sha256']
subprocess.run(['git','-C',str(tree),'diff','--check'],check=True)
assert not subprocess.check_output(['git','-C',str(tree),'branch','--show-current'],text=True).strip()
subprocess.run(['git','-C',str(tree),'switch','-c','samurai-geometry305'],capture_output=True,check=True)
subprocess.run(['git','-C',str(tree),'add','--','drivers/media/i2c/s5k3m5.c'],check=True)
message='''media: i2c: report S5K3M5 active array and mode crop geometry

The sensor returned binned output dimensions as the crop bounds and
omitted the default crop and native size. libcamera therefore substituted
the output size for the pixel array and warned about incomplete geometry.

Report the 4208x3120 active array relative to its first pixel, and keep
each mode's analogue crop separate from the binned output dimensions.
The 24 MHz cropped mode starts 376 active rows below the array origin;
the 19.2 MHz full-field binned mode uses the complete active array.
Use the selected ACTIVE or TRY format when reporting the mode crop.

The RMX1931 19.2 MHz profile passed eight selection queries, property
enumeration, four-camera switching and interrupted capture/reopen.
The 24 MHz modes were checked against their register tables but were
not exercised on the handset. Register tables and board DT are unchanged.
'''
subprocess.run(['git','-C',str(tree),'commit','-F','-'],input=message.encode(),capture_output=True,check=True)
commit=subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','-C',str(tree),'status','--porcelain'])
report=dict(stage=305,branch='samurai-geometry305',commit=commit,tree=str(tree),source_clean=True,
 source_sha256=expected['source_sha256'],base_commit='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117',
 original298_tree_unchanged=True,only_sensor_source_changed=True,
 deployed_sensor_module_sha256=expected['module_sha256'],deployed_image_still298=True,not_pushed=True)
(HERE/'kernel-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
