"""Read-only source audit. Does not access USB, serial, or target registers."""
from pathlib import Path
import gzip, hashlib, json, re, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel69')
kernel = Path('/home/cy122/x2pro-linux/linux')
stock = Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
stock_commit = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
quic_commit = '693741a3b0448690402539ed0e6af067510e386f'
sources = {}

def snapshot(name, data, origin, patterns):
    (out / (name + '.source.gz')).write_bytes(gzip.compress(data, mtime=0))
    lines = data.decode().splitlines()
    matches = []
    for n, line in enumerate(lines, 1):
        if any(re.search(p, line) for p in patterns):
            matches.append({'line': n, 'text': line})
    sources[name] = {'origin': origin, 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest(), 'matches': matches}

local = [
    ('tty-eud', 'drivers/tty/serial/eud.c', ['CSR_EUD_EN', 'Only RX', 'VBUS', r'writel\(\(u32\)EUD_INT_RX']),
    ('mainline-eud-control', 'drivers/usb/misc/qcom_eud.c', ['usb_role_switch', 'EUD_INT_VBUS', 'VBUS_INT_CLR']),
    ('dwc3-qcom-legacy', 'drivers/usb/dwc3/dwc3-qcom-legacy.c', ['qcom,dwc3', 'vbus_override_enable', 'usb_get_dr_mode', 'extcon', 'dwc3-qcom-legacy']),
    ('dwc3-qcom-new', 'drivers/usb/dwc3/dwc3-qcom.c', ['qcom,snps-dwc3', 'usb_get_dr_mode', 'dwc3-qcom']),
    ('dwc3-makefile', 'drivers/usb/dwc3/Makefile', ['QCOM', 'DUAL_ROLE', 'drd.o']),
    ('sm8150', 'arch/arm64/boot/dts/qcom/sm8150.dtsi', ['qcom,sm8150-dwc3', 'qcom,dwc3', 'usb_1:', 'usb_1_dwc3:']),
    ('sm8150-mtp', 'arch/arm64/boot/dts/qcom/sm8150-mtp.dts', ['usb_1', 'dr_mode']),
    ('samurai', 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts', ['eud', 'sm8150-mtp', 'usb-role-switch', 'extcon']),
    ('kernel-config', '.config', ['USB_DWC3[=_]', 'USB_QCOM_EUD', 'USB_CONFIGFS', 'TYPEC_QCOM_PMIC']),
]
for name, rel, patterns in local:
    snapshot(name, (kernel / rel).read_bytes(), str(kernel / rel), patterns)
snapshot('actual-init', Path('/home/cy122/x2pro-linux/initramfs/init').read_bytes(),
         '/home/cy122/x2pro-linux/initramfs/init', ['configfs', 'ttyEUD0', 'usb_gadget'])
for name, rel, patterns in [
    ('stock-eud', 'drivers/soc/qcom/eud.c', ['extcon', 'EUD_INT_VBUS', 'usb_attach', 'VBUS_INT_CLR']),
    ('stock-dwc3-msm', 'drivers/usb/dwc3/dwc3-msm.c', ['extcon', 'vbus_notifier', 'vbus_active']),
    ('stock-usb-dts', 'arch/arm64/boot/dts/qcom/sm8150-usb.dtsi', ['extcon', 'eud', 'dr_mode']),
]:
    data = subprocess.check_output(['git', '--git-dir=' + str(stock), 'show', stock_commit + ':' + rel])
    snapshot(name, data, {'repository': str(stock), 'commit': stock_commit, 'path': rel}, patterns)
snapshot('quic-ctl-api', Path('/mnt/e/eud-host/quic-eud/src/ctl_api.cpp').read_bytes(),
         {'repository': 'https://github.com/quic/eud', 'commit': quic_commit, 'path': 'src/ctl_api.cpp'},
         ['MSM USB', 'EUD to host', 'eud_connect_usb', 'eud_spoof_attach', 'CTL_VBUS'])
snapshot('installed-eudtool-source', Path('/mnt/e/eud-host/eudtool.cpp').read_bytes(),
         'E:/eud-host/eudtool.cpp', ['vbusAttach', 'VBUS_ATTACH', 'VBUS_INT', 'com-up'])
info = {
    'kernel_head': subprocess.check_output(['git', '-C', str(kernel), 'rev-parse', 'HEAD']).decode().strip(),
    'sources': sources,
    'findings': {
        'no_intrinsic_exclusivity_claim': True,
        'quic_describes_msm_usb_through_eud': True,
        'tty_eud_vbus_notification_forwarding': False,
        'mainline_control_is_module_without_runtime_module': True,
        'dt_matches_legacy_glue': True,
        'legacy_peripheral_sets_vbus_override': True,
        'gadget_function_directory_empty_verified': True,
        'coexistence_hardware_tested': False,
        'missing_vbus_forwarding_is_proven_root_cause': False,
        'android_exclusivity': 'User observation; Android is not currently booted or retested.',
        'native_usb_or_control_changes_this_session': False,
    },
    'primary_sources': [
        'https://github.com/quic/eud/blob/' + quic_commit + '/src/ctl_api.cpp',
        'https://android.googlesource.com/kernel/msm/+/f382bd87e7398d1d55b1b84211de3d44ae88cf11/Documentation/devicetree/bindings/soc/qcom/qcom,msm-eud.txt',
        'https://android.googlesource.com/kernel/common/+/aa2d7f4e5b5f104324e9671a102420087f0afba4/drivers/usb/misc/qcom_eud.c',
        'https://docs.kernel.org/usb/gadget_configfs.html',
        'https://postmarketos.org/edge/2025/12/28/USB-framework-rework/',
        'https://gitlab.com/postmarketOS/pmaports/-/merge_requests/3819',
    ],
    'lookup_limits': [
        'Local kernel HEAD e42788e is a project EUD-console commit, not a public torvalds commit. Its raw GitHub URL returned 404.',
        'lore.kernel.org patch-series page returned 403; pending newer platform patches are not used as deployed-code evidence.',
        'Initial multi-file BusyBox readlink invocation was invalid; its validated output is retained and separate single-path queries are used.',
        'Initially read dwc3-qcom.c; corrected actual matching path to dwc3-qcom-legacy.c before any change.',
        'USB_Network and SSH wiki pages redirected to wiki.nura.eco and were denied by site protection; no bypass attempted. The official USB rework notice was readable.',
    ],
}
(out / 'source-audit.json').write_text(json.dumps(info, indent=2, ensure_ascii=False) + '\n')
print('Source snapshots:', len(sources))
print(json.dumps(info['findings'], indent=2, ensure_ascii=False))
