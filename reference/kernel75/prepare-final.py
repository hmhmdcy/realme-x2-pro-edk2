from pathlib import Path
import hashlib, difflib, json

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel75')
kernel = Path('/home/cy122/x2pro-linux/linux')
relative = 'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_dsc.c'
path = kernel/relative
before = (out/'dpu_hw_dsc.c.before').read_text()
current = path.read_text()
patch = 'diff --git a/'+relative+' b/'+relative+'\n'+''.join(
    difflib.unified_diff(before.splitlines(True), current.splitlines(True),
                         'a/'+relative, 'b/'+relative))
assert patch == (ref/'dsc-diagnostic.patch').read_text()
assert not (out/'dpu_hw_dsc.c.diagnostic').exists()
(out/'dpu_hw_dsc.c.diagnostic').write_text(current)
path.write_text(before)
(ref/'build-final.sh').write_text((ref/'build-noncontinuous.sh').read_text().replace('noncontinuous','final'))
(ref/'prepare-final-flash.py').write_text((ref/'prepare-noncontinuous-flash.py').read_text().replace('noncontinuous','final'))
(out/'final-source-manifest.json').write_text(json.dumps({
    'removed_readonly_dsc_diagnostic': True,
    'sources': {n: hashlib.sha256((kernel/n).read_bytes()).hexdigest() for n in [
        'drivers/gpu/drm/panel/panel-samsung-sofef03f.c',
        'drivers/gpu/drm/msm/dsi/dsi_host.c', relative,
        'drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c',
        'drivers/gpu/drm/msm/disp/dpu1/dpu_kms.h',
        'drivers/gpu/drm/msm/disp/dpu1/dpu_rm.c',
        'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c',
        'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c',
        'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.h',
        'arch/arm64/boot/dts/qcom/sm8150-samurai.dts']}
}, indent=2)+'\n')
print('Removed only read-only DSC diagnostics; retained accepted noncontinuous/EOT configuration.')
