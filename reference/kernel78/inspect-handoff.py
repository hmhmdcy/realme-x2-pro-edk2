from pathlib import Path
import re

root = Path('/home/cy122/x2pro-linux/linux')
files = {
    'drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c': ['dpu_kms_hw_init'],
    'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c': [
        'dpu_hw_intf_clear_boot_config', 'dpu_hw_intf_disable_autorefresh',
        'dpu_hw_intf_connect_external_te'],
    'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c': ['dpu_hw_ctl_clear_boot_config'],
    'drivers/gpu/drm/msm/disp/dpu1/dpu_rm.c': ['dpu_rm_clear_boot_config'],
    'drivers/gpu/drm/msm/dsi/dsi.c': ['dsi_bind'],
    'drivers/gpu/drm/msm/dsi/phy/dsi_phy.c': ['msm_dsi_phy_pll_save_state', 'msm_dsi_phy_pll_restore_state'],
}
result = []
for name, functions in files.items():
    src = (root / name).read_text()
    result.append('\nFILE ' + name)
    for fn in functions:
        match = re.search(r'(?m)^(?:static )?[^\n;]*\b' + fn + r'\s*\([^;]*?\)\s*\{', src)
        if not match:
            result.append('MISSING ' + fn)
            continue
        start = match.start()
        end = src.index('{', start) + 1
        depth = 1
        while depth:
            depth += (src[end] == '{') - (src[end] == '}')
            end += 1
        result.append(f'LINE {src[:start].count(chr(10)) + 1}\n' + src[start:end])
report = '\n'.join(result) + '\n'
Path('/mnt/e/edk2-samurai-out/kernel78/handoff-functions.txt').write_text(report)
print(report)
