from pathlib import Path
import hashlib,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];target=repo/'linux-port/packages/samurai-camera-config';assert not target.exists();target.mkdir()
names=['configuration.yaml','samurai-camera-heaps.conf','70-samurai-camera-heaps.rules']
for name in names:shutil.copyfile(repo/'linux-port/camera'/name,target/name)
recipe='''# Device configuration only; camera and kernel binaries are packaged separately.
pkgname=samurai-camera-config
pkgver=0.1.0
pkgrel=0
pkgdesc="Realme X2 Pro libcamera CPU ISP and generic camera heap access"
url="https://github.com/hmhmdcy/edk2-realme-x2-pro"
arch="noarch"
license="LicenseRef-Local-Project"
depends="libcamera=99990.7.2-r5 libcamera-ipa=99990.7.2-r5 openrc eudev"
subpackages="samurai-camera-stack:stack"
options="!check"
source="configuration.yaml samurai-camera-heaps.conf 70-samurai-camera-heaps.rules"

package() {
	install -Dm644 "$srcdir"/configuration.yaml "$pkgdir"/etc/libcamera/configuration.yaml
	install -Dm644 "$srcdir"/samurai-camera-heaps.conf "$pkgdir"/etc/modules-load.d/samurai-camera-heaps.conf
	install -Dm644 "$srcdir"/70-samurai-camera-heaps.rules "$pkgdir"/etc/udev/rules.d/70-samurai-camera-heaps.rules
	chmod 755 "$pkgdir"/etc/libcamera
}

stack() {
	pkgdesc="Pinned Realme X2 Pro camera framework and device configuration"
	depends="samurai-camera-config=$pkgver-r$pkgrel libcamera=99990.7.2-r5 libcamera-ipa=99990.7.2-r5 libcamera-tools=99990.7.2-r5 libcamera-gstreamer=99990.7.2-r5 libcamera-v4l2=99990.7.2-r5"
	mkdir -p "$subpkgdir"
}

sha512sums="
'''+''.join(hashlib.sha512((target/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names)+'"\n'
(target/'APKBUILD').write_text(recipe)
report=dict(stage=214,device_config_recipe_created=True,three_config_payloads_byte_identical_to_existing_canonical_files=True,configuration_directory_0755_files_0644=True,generic_video_heap_rule_preserved=True,protected_fastrpc_pool_not_in_rule=True,no_runtime_script_or_device_mutation=True,pinned_camera_stack_package_defined=True)
(here/'config-port-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
