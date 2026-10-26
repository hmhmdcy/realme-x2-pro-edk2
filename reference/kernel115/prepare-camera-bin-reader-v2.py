from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
t=(root/'extract-camera-bins.sh').read_text()
t=t.replace('k115-vendor-camera-bins','k115-vendor-camera-bins-v2').replace('k115-camera-bins-vendor-readonly','k115-camera-bins-vendor-readonly-v2')
t=t.replace('-maxdepth 1','-maxdepth 4')
t=t.replace('cp -p "$file" "$dest/modules/"','relative=${file#"$mp/etc/camera/"}\n    mkdir -p "$dest/modules/$(dirname "$relative")"\n    test ! -e "$dest/modules/$relative"\n    cp -p "$file" "$dest/modules/$relative"')
(root/'extract-camera-bins-v2.sh').write_text(t)
print('Camera BIN reader now covers project subdirectories and preserves paths')
