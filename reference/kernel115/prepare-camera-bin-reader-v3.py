from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
t=(root/'extract-camera-bins-v2.sh').read_text()
t=t.replace('k115-vendor-camera-bins-v2','k115-vendor-camera-bins-v3').replace('k115-camera-bins-vendor-readonly-v2','k115-camera-bins-vendor-readonly-v3')
t=t.replace('$mp/etc/camera','$mp/lib64/camera').replace("-name '*sensor*.bin'","-name 'com.qti.sensormodule.*.bin'")
(root/'extract-camera-bins-v3.sh').write_text(t)
print('Camera BIN reader uses observed lib64/camera sensormodule paths')
