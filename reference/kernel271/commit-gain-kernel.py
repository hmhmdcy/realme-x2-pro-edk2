"""Commit only the tested sensor-control change; preserve earlier branches."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent
assert json.loads((R/'three-camera-regression-validation.json').read_text())['passed']
assert json.loads((R/'gain-response-validation.json').read_text())['physical_fractional_gain_verified']
K=Path('/home/cy122/x2pro-linux/camera270-kernel')
assert subprocess.check_output(['git','branch','--show-current'],cwd=K,text=True).strip()=='samurai-camera-gain271'
assert subprocess.check_output(['git','diff','--name-only'],cwd=K,text=True).splitlines()==['drivers/media/i2c/s5k3m5.c']
subprocess.run(['git','diff','--check'],cwd=K,check=True)
subprocess.run(['git','add','--','drivers/media/i2c/s5k3m5.c'],cwd=K,check=True)
message='''media: i2c: expose native S5K3M5 analogue gain codes

The sensor resolves gain in steps of 1/32, from code 32 (unity) to
512 (16x). The integer multiplier control discarded intermediate values.
Expose the native code range and write the selected value directly.

Pair this control change with a userspace sensor helper using gain=code/32.
The RMX1931 19.2 MHz profile passed physical fractional-gain response and
front/rear switching tests; the existing 24 MHz profile was not exercised.
'''
subprocess.run(['git','commit','-F','-'],cwd=K,input=message.encode(),check=True,capture_output=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=K,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=K)
report=dict(stage=271,branch='samurai-camera-gain271',commit=commit,source_clean=True,
 source_sha256=hashlib.sha256((K/'drivers/media/i2c/s5k3m5.c').read_bytes()).hexdigest(),previous_branches_preserved=True,not_pushed=True)
(R/'kernel-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
