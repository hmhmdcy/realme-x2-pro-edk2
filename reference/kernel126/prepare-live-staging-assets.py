from pathlib import Path
import runpy,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');runpy.run_path(str(ref/'ensure-build-volume.py'));v=Path('/home/cy122/pmos-samurai-build126')
script=v/'rootfs/usr/sbin/samurai-bluetooth';assert script.resolve().is_relative_to(v/'rootfs');data=script.read_bytes();(out/'bluetooth-script-k126-private').write_bytes(data)
report=dict(bluetooth_script_sha256=hashlib.sha256(data).hexdigest(),module_archive_sha256=json.loads((ref/'kernel-build-validation.json').read_text())['archive_sha256'],release='7.3.0-rc6-rmx1931-samurai-k126+',old118_module_directory_will_remain=True,only_current_release_bluetooth_path_changes=True)
(ref/'live-staging-assets-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
