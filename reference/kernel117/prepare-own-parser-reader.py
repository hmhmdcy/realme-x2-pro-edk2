from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
t=(root/'extract-camera-sources.sh').read_text()
t=t.replace('k115-vendor-camera-source','k117-vendor-generated-source').replace('k115-camera-vendor-readonly','k117-generated-vendor-readonly')
t=t.replace('test -d "$mp/lib64/camera"','test -d "$mp/lib64"')
t=t.replace('find "$mp/lib64/camera" -maxdepth 1 -type f -name \'com.qti.sensor.*.so\' > "$dest/module-paths-private.txt"',
'''find "$mp/lib64" -maxdepth 1 -type f -name '*camx*.so' -exec stat -c '%s %n' '{}' ';' > "$dest/camx-module-metadata-private.txt"
find "$mp/lib64" -maxdepth 1 -type f -name '*camxgenerated*.so' > "$dest/module-paths-private.txt"''')
t=t.replace('SAME_HANDSET_CAMERA_SENSOR_MODULES_EXTRACTED_READONLY','SAME_HANDSET_GENERATED_CAMERA_PARSER_EXTRACTED_READONLY')
(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel117')/'extract-own-generated-parser.sh').write_text(t)
print('Own generated-parser readonly reader prepared')
