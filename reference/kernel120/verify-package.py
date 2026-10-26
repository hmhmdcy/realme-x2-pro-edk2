from pathlib import Path
import runpy,tarfile,hashlib,json,re
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
k=Path('/home/cy122/pmos-samurai-kernel118/camera120/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel120');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
release=(k/'include/config/kernel.release').read_text().strip()
expected=json.loads((ref/'kernel-build-validation.json').read_text())['image_and_module_hashes']
assert sha(out/'Image-k120-private')==expected['arch/arm64/boot/Image']
assert sha(out/'sm8150-samurai-k120-private.dtb')==expected['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']
assert (out/'depmod-check-private.txt').stat().st_size==0
with tarfile.open(out/'modules-k120-private.tar.gz') as tf:
    members=tf.getmembers();modules=[m for m in members if m.isfile() and m.name.endswith('.ko')]
    assert len(modules)==770 and not any(m.issym() for m in members)
    assert all((m.isdir() and m.name in ['lib/modules','lib/modules/'+release] or m.name.startswith('lib/modules/'+release+'/')) and '..' not in Path(m.name).parts and (m.isdir() or m.isfile()) for m in members)
    dep=tf.extractfile('lib/modules/'+release+'/modules.dep').read().decode()
    known={m.name.removeprefix('lib/modules/'+release+'/') for m in modules}
    for line in dep.splitlines():
        module,deps=line.split(':',1);assert module in known
        assert all(name in known for name in deps.split())
report=dict(candidate=120,matched_image_dtb_copies=True,module_archive_count=770,no_symlinks=True,all_module_dependencies_in_archive=True,depmod_system_map_no_diagnostics=True,archive_sha256=sha(out/'modules-k120-private.tar.gz'),archive_bytes=(out/'modules-k120-private.tar.gz').stat().st_size,full_rootfs120_not_generated=True,not_deployed=True)
(ref/'package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
