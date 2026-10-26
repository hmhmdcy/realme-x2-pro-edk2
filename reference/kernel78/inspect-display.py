from pathlib import Path
import hashlib
import re
import subprocess

root = Path('/home/cy122/x2pro-linux/linux')
out = Path('/mnt/e/edk2-samurai-out/kernel78')
files = {
    'drivers/gpu/drm/msm/dsi/dsi_host.c': [
        'dsi_sw_reset', 'dsi_ctrl_enable', 'dsi_ctrl_disable', 'msm_dsi_host_power_on',
        'msm_dsi_host_power_off', 'msm_dsi_host_enable',
        'msm_dsi_host_disable', 'dsi_err_worker', 'dsi_fifo_status',
        'msm_dsi_host_init', 'msm_dsi_host_reset_phy', 'dsi_op_mode_config'],
    'drivers/gpu/drm/msm/dsi/dsi_manager.c': [
        'dsi_mgr_bridge_pre_enable', 'dsi_mgr_bridge_post_disable',
        'dsi_mgr_phy_enable', 'dsi_mgr_phy_disable', 'dsi_mgr_bridge_power_on'],
    'drivers/gpu/drm/msm/dsi/phy/dsi_phy.c': [
        'msm_dsi_phy_enable', 'msm_dsi_phy_disable'],
    'drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c': [
        'dsi_7nm_phy_enable', 'dsi_7nm_phy_disable', 'dsi_7nm_pll_save_state',
        'dsi_7nm_pll_restore_state', 'dsi_pll_7nm_vco_recalc_rate',
        'dsi_pll_7nm_vco_set_rate', 'dsi_7nm_set_usecase',
        'dsi_pll_7nm_init', 'dsi_7nm_set_continuous_clock'],
}
result = []
hashes = {}
for name, functions in files.items():
    path = root / name
    raw = path.read_bytes()
    hashes[name] = hashlib.sha256(raw).hexdigest()
    src = raw.decode()
    result.append('\nFILE ' + name)
    for fn in functions:
        match = re.search(r'(?m)^(?:static )?[^\n;]*\b' + fn + r'\s*\([^;]*?\)\s*\{', src)
        if not match:
            result.append('MISSING ' + fn)
            continue
        start = match.start()
        pos = src.index('{', start)
        depth = 1
        end = pos + 1
        while depth:
            if src[end] == '{':
                depth += 1
            elif src[end] == '}':
                depth -= 1
            end += 1
        line = src[:start].count('\n') + 1
        result.append(f'LINE {line}\n' + src[start:end])
report = '\n'.join(result) + '\n'
(out / 'display-functions.txt').write_text(report)
(out / 'display-source-hashes.txt').write_text('\n'.join(f'{v}  {k}' for k, v in hashes.items()) + '\n')
print(report)
print(subprocess.run(['git', 'diff', '--stat'], cwd=root, capture_output=True, text=True).stdout)
