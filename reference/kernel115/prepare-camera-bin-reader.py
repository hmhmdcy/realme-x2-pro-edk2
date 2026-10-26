from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
t=(root/'extract-camera-sources.sh').read_text()
t=t.replace('k115-vendor-camera-source','k115-vendor-camera-bins').replace('k115-camera-vendor-readonly','k115-camera-bins-vendor-readonly')
t=t.replace('"$mp/lib64/camera"','"$mp/etc/camera"').replace("-name 'com.qti.sensor.*.so'","-name '*sensor*.bin'")
t=t.replace('mkdir -m700 "$dest/modules"','find "$mp/etc/camera" -maxdepth 1 -type f -exec stat -c "%s %n" \'{}\' \';\' > "$dest/camera-file-list-private.txt"\nmkdir -m700 "$dest/modules"')
t=t.replace('k115-vendor-camera-source-private','k115-vendor-camera-bins-private').replace('SAME_HANDSET_CAMERA_SENSOR_MODULES_EXTRACTED_READONLY','SAME_HANDSET_CAMERA_SENSOR_BINARIES_EXTRACTED_READONLY')
(root/'extract-camera-bins.sh').write_text(t)
print('Bounded camera BIN reader prepared')
