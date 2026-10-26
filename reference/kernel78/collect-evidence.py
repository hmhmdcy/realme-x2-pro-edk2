from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil
import subprocess

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel78')
linux = Path('/home/cy122/x2pro-linux/linux')
expected = {
    'before': 'e84a1dbe33478854e1887af74e80bac7a8367c2902418ec8808a2671210fbd5c',
    'fresh': '3db17f16e782002e130183e4c4fc0471c49f2f73bb33a9dd2c9d32e0f0728071',
    'late': '84fd76052d42940caaffff7f51f3ec546091fcaa90e80c7a237efd7fef31cb8c',
    'repeat': '9c7529bad62dcd118055b156aaea2d47792f0b50200f2dfdf0114734bb48c7d0',
    'after-refresh': '2a0d1e2485732b78e1e01ce588bb986ddf7e756e838e011dbb34bb219a7d7962',
    'complete': '56eeaf8611af4915122806f8fa7895972c978e6625ed0fbb095664fae50d5773',
}
logs = []
for prefix, sha in expected.items():
    path = out / (prefix + '-dmesg.txt.gz')
    raw = gzip.decompress(path.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == sha
    (ref / (prefix + '-dmesg.txt')).write_bytes(raw)
    shutil.copyfile(path, ref / path.name)
    text = raw.decode()
    faults = re.findall(r'(?mi)^.*(?:\bBUG:|\bOops:|\bKernel panic|\bUnhandled fault|SMMU.*context fault|geni_i2c.*(?:error|timeout)).*$', text)
    assert not faults
    logs.append({
        'prefix': prefix, 'raw_bytes': len(raw), 'sha256': sha,
        'dsi_worker_status_messages': text.count('dsi_err_worker: status='),
        'dsi_worker_matching_lines': sum('dsi_err_worker' in row for row in text.splitlines()),
        'inherited_frame_stalled': 'boot INTF1 frame stalled:' in text,
        'panel_enable_messages': text.count('DSC 1080x2400@60'),
        'last_kernel_timestamp': float(re.findall(r'\[\s*([0-9.]+)\]', text)[-1]),
        'matched_faults': faults,
    })
files = [
    'healthy-kms.txt', 'healthy-state.txt', 'fresh-kms.txt', 'fresh-state.txt',
    'late-kms.txt', 'late-clocks.txt', 'repeat-kms.txt', 'repeat-clocks.txt',
    'after-refresh-kms.txt', 'complete-kms.txt', 'kms-diff.json',
    'display-functions.txt', 'display-source-hashes.txt', 'handoff-functions.txt',
    'refresh.txt', 'refresh-validation.json', 'pageflip.txt', 'pageflip-validation.json',
    'final-device-state.txt', 'final-usbipd.txt',
]
for name in files:
    shutil.copyfile(out / name, ref / name)
for prefix in ('snapshot', 'late', 'repeat'):
    events = [json.loads(row) for row in (out / (prefix + '-f1-wsl.events.jsonl')).read_text().splitlines()]
    assert sum(row.get('event') == 'out_submit' for row in events) == 1
    assert any(row.get('event') == 'receipt' and row.get('text') == 'F1' for row in events)
    reboot = json.loads((out / (prefix + '-reboot.json')).read_text(encoding='utf-8-sig'))
    assert reboot['reboot_success'] and not reboot['boot_written'] and not reboot['logdump_written']
    for path in out.glob(prefix + '-*.out'):
        shutil.copyfile(path, ref / path.name)
    for path in out.glob(prefix + '-*.err'):
        shutil.copyfile(path, ref / path.name)
    for suffix in ('-f1-wsl.events.jsonl', '-f1-wsl.meta.json', '-reboot.json'):
        path = out / (prefix + suffix)
        if path.exists():
            shutil.copyfile(path, ref / path.name)
config = (linux / '.config').read_text()
assert 'CONFIG_DRM_MSM_DSI_7NM_PHY=y' in config
assert '# CONFIG_DRM_MSM_DSI_10NM_PHY is not set' in config
dtsi = (linux / 'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text()
assert dtsi.count('compatible = "qcom,dsi-phy-7nm-8150";') == 2
phy_path = 'drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c'
base = subprocess.check_output(['git', 'show', 'HEAD:' + phy_path], cwd=linux)
assert (linux / phy_path).read_bytes() == base
binding = {
    'dt_compatible': 'qcom,dsi-phy-7nm-8150', 'driver': phy_path,
    'config': 'CONFIG_DRM_MSM_DSI_7NM_PHY=y', '10nm_driver_disabled': True,
    'quirk': 'DSI_PHY_7NM_QUIRK_V4_0',
    'kernel_source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=linux, text=True).strip(),
    'driver_sha256': hashlib.sha256(base).hexdigest(), 'driver_unchanged_from_source_head': True,
}
(ref / 'phy-binding-validation.json').write_text(json.dumps(binding, indent=2) + '\n')
facts = {
    'session': 78, 'kernel_build': 76,
    'firmware_or_kernel_deployment': False, 'partition_writes': [],
    'boot_sha256_readback': '3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e',
    'logdump_sha256_readback': '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0',
    'new_boot_ids': ['7ccf5e4b-7cd9-424f-b91c-d3bf5f529f57', '931c82bf-e465-47db-b800-a7a26cef50b0', 'e1a36cea-f401-41f2-bd1a-1eedf1282e96'],
    'current_boot_id': 'e1a36cea-f401-41f2-bd1a-1eedf1282e96',
    'current_taint': 0, 'current_uptime_at_final_receipt_seconds': 668.74,
    'current_dsi_worker_messages': 0, 'current_panel_enable_messages': 1,
    'current_gauge': {'pack_voltage_uV': 8645000, 'current_uA': 0, 'temp_deciC': 297, 'capacity_percent': 100, 'reported_status': 'Not charging'},
    'no_charge_gauge_config_nvm_otg_or_fastcharge_mcu_access': True,
    'physical_optical_observation': False, 'intermittent_display_failure_fixed': False,
    'logs': logs,
}
(ref / 'hardware-validation.json').write_text(json.dumps(facts, indent=2) + '\n')
print(json.dumps({'logs': logs, 'phy': binding, 'current_boot_id': facts['current_boot_id']}, indent=2))
