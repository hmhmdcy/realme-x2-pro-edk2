from pathlib import Path
import hashlib, json, subprocess

root=Path('/home/cy122/pmos-samurai-rootfs114/rootfs')
out=Path('/mnt/e/edk2-samurai-out/kernel114')
public=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114')
def run(*args):
    return subprocess.check_output(['chroot',str(root),*args],text=True,stderr=subprocess.STDOUT)
packages=run('apk','info').splitlines()
required=['postmarketos-ui-phosh','phosh','phoc','mesa-dri-gallium','networkmanager','modemmanager','qmi-utils','libcamera-tools','calls','chatty','firefox','mobile-config-firefox','megapixels','rsync','strace','openssh-server-pam','bluez','pulseaudio','hexagonrpcd']
assert all(p in packages for p in required)
files=['usr/local/bin/samurai-phosh-session','usr/local/sbin/samurai-usb','usr/sbin/samurai-wifi','usr/sbin/samurai-radio-address','usr/sbin/samurai-bt-address','usr/sbin/samurai-rmtfs-cow','usr/sbin/samurai-tqftpserv','usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf','usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf','etc/greetd/samurai-phosh.toml','usr/bin/qmicli','usr/bin/cam']
assert all((root/p).is_file() for p in files)
for link in ['bin','sbin','lib']:
    assert (root/link).is_symlink()
run('/usr/sbin/sshd.pam','-t')
run('glib-compile-schemas','--strict','/usr/share/glib-2.0/schemas')
run('/bin/sh','-n','/usr/local/bin/samurai-phosh-session','/usr/sbin/samurai-wifi','/etc/init.d/samurai-radio','/etc/init.d/samurai-loopback','/etc/init.d/samurai-usb')
for level,services in [('boot',['samurai-usb','samurai-loopback','sshd']),('default',['greetd','networkmanager','samurai-radio'])]:
    assert all((root/f'etc/runlevels/{level}/{s}').is_symlink() for s in services)
assert not any((root/f'etc/runlevels/{level}/hexagonrpcd').exists() for level in ['boot','default'])
release=(root/'etc/samurai-rootfs-release').read_text()
assert 'ROOTFS_ID=samurai-f2fs-rootfs01\n' in release
report=dict(package_count=len(packages),required_packages=required,userspace_validation_pass=True,
            rootfs_compatible_kernel_build=113,new_kernel_deployed=False,new_rootfs_deployed=False,
            hardware_complete=False,goal_complete=False,static_export_and_import_files=13254,
            files_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files},
            missing_functionality=['display_gpu_stability','5ghz_current_regression','full_sensor_service','ipa_cellular_data','calls','gnss','camera_capture','fingerprint','suspend_resume','otg_acceptance','audio_acoustic_acceptance','charging_control'])
(out/'userspace-complete.json').write_text(json.dumps(report,indent=2)+'\n')
(public/'userspace-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'packages-installed.txt').write_text('\n'.join(packages)+'\n')
print(json.dumps(dict(package_count=len(packages),required_packages_pass=True,services_and_schemas_pass=True,hardware_complete=False)))
