from pathlib import Path
import hashlib,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
out=Path('/mnt/e/edk2-samurai-out/kernel154')
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
build=(ref/'build-package.py').read_text()
for label,statement in [
    ('dsi-w1',"make('dsi-w1',['W=1','-j4','drivers/gpu/drm/msm/dsi/dsi_host.o'])"),
    ('full',"make('full',['-j4','Image','modules','qcom/sm8150-samurai.dtb'])")]:
    assert statement in build
    log=out/(label+'-build-private.log')
    assert log.exists() and 'error:' not in log.read_text() and 'warning:' not in log.read_text()
    build=build.replace(statement,"print('K154_REUSE_COMPLETED_"+label.upper()+"',flush=True)")
assert (out/'Image-k154-host-init-private').read_bytes()==(k/'arch/arm64/boot/Image').read_bytes()
(out/'package-resume-validation.json').write_text(json.dumps(dict(
    completed_full_build_retained=True,failed_at_existing_old_module_directory_guard=True,
    intended_new_module_directory='modules-root154',prior_modules_untouched=True,
    generated_image_sha256=hashlib.sha256((k/'arch/arm64/boot/Image').read_bytes()).hexdigest()),indent=2)+'\n')
exec(compile(build,str(ref/'build-package.py'),'exec'))
