from pathlib import Path
import ast, hashlib, json, re

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel171')
header = (out / 'audio-kernel/asoc/msm-dai-q6-v2.h').read_text()
driver = (out / 'audio-kernel/asoc/msm-dai-q6-v2.c').read_text()
overlay = (out / 'arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi').read_text()
pins = (out / 'arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi').read_text()
assert '#define MSM_MI2S_SD0 (1 << 0)' in header and '#define MSM_MI2S_SD1 (1 << 1)' in header
section = overlay.split('&dai_mi2s3 {', 1)[1].split('};', 1)[0]
assert 'qcom,msm-mi2s-rx-lines = <2>;' in section
assert 'mi2s_pdata->rx_sd_lines = rx_line;' in driver
assert 'case MSM_MI2S_SD1:\n\t\t\t*config_ptr = AFE_PORT_I2S_SD1;' in driver
pinsection = pins.split('quat_mi2s_sd1_active:', 1)[1].split('\n\t\t};', 1)[0]
assert 'pins = "gpio140";' in pinsection and 'function = "qua_mi2s";' in pinsection
hotdog = (out / 'hotdog-reference/aports/device/testing/linux-oneplus-hotdog-mainline616/0039-asoc-hotdog-enable-bounded-tfa9874-speaker-output.patch').read_text()
assert 'qcom,sd-lines = <1>;' in hotdog and 'pins = "gpio140";' in hotdog
def detector(path):
    return next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'analyze_samples')
assert ast.dump(detector(ref / 'analyze-acoustic.py')) == ast.dump(detector(ref.parent / 'kernel170/analyze-acoustic.py'))
source = Path('/home/cy122/pmos-samurai-kernel136/kernel/sound/soc/qcom/qdsp6/q6afe-dai.c').read_text()
assert 'priv->sd_line_mask |= BIT(lines[i]);' in source
afe = Path('/home/cy122/pmos-samurai-kernel136/kernel/sound/soc/qcom/qdsp6/q6afe.c').read_text()
assert 'case AFE_PORT_I2S_SD1_MASK:\n\t\t\tpcfg->i2s_cfg.channel_mode = AFE_PORT_I2S_SD1;' in afe
report = dict(stage=171, oem_pinned_commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6',
              oem_rx_bitmask=2, oem_rx_maps_to='SD1', oem_sd1_pin=140,
              prior_native_sd_line_index=0, prior_native_pin=139,
              corrected_native_sd_line_index=1, corrected_native_pin=140,
              oneplus_hotdog_independent_patch_matches_sd1=True,
              oneplus_amp_is_tfa9874_realme_amp_is_max98937=True,
              amplifier_driver_not_transplanted=True,
              detector_function_identical_to_tested170=True,
              primary_sources=[
                  'https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi',
                  'https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/audio-kernel/asoc/msm-dai-q6-v2.h',
                  'https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0039-asoc-hotdog-enable-bounded-tfa9874-speaker-output.patch'])
(ref / 'contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
