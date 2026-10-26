"""Hash cached sources and record plan scope only. No kernel implementation."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
SNAP = REF / 'charging-oem-audit-20261023/apsd-integration/current-r7/snapshots'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
link = read(SNAP.parent / 'image-source-linkage.json')
comparisons = {x['path']: x for x in link['comparisons']}
files = {}
for relative in ['drivers/tty/serial/eud.c', 'drivers/tty/serial/eud_earlycon.c',
                 'drivers/usb/misc/qcom_eud.c', 'drivers/usb/dwc3/dwc3-qcom-legacy.c',
                 'drivers/usb/dwc3/dwc3-qcom.c', 'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c']:
    path = SNAP / relative.replace('/', '--')
    expected = comparisons[relative]
    assert expected['byte_equal_to_original_image_source']
    assert sha(path) == expected['base_sha256'] == expected['current_sha256']
    files[str(path.relative_to(REF)).replace('\\', '/')] = sha(path)
selected = [SNAP / 'arch--arm64--boot--dts--qcom--sm8150.dtsi',
            SNAP / 'arch--arm64--boot--dts--qcom--sm8150-samurai.dts', SNAP / 'build--.config',
            REF / 'charging-session-20261023/gauge-image501-carriers-candidate/PlatformBm.c.candidate',
            REF / 'charging-oem-audit-20261023/eud-boot-policy/EudLogDxe.c',
            REF / 'charging-oem-audit-20261023/eud-boot-policy/EudSerialPortLib.c',
            REF / 'charging-oem-audit-20261023/apsd-pd5v-client-bridge-candidate/samurai-apsd-owner.c',
            REF / 'charging-session-20261023/eud-runtime-window-candidate-r2/eud.c']
for path in selected: files[str(path.relative_to(REF)).replace('\\', '/')] = sha(path)
assert sha(selected[3]) == 'cfae4eef298d751b41b11e326c32f9330ecfc3d55b87b53cf45d1087d44ffd21'
assert sha(selected[6]) == 'd05d4f81f8427cfbe7cd37c458b538d0ee60a2e9422c243cdf13fa6ba246d979'
post = read(Path('E:/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/postboot-r1-04-private/stdout-private.json'))
nodes = post['raw']['eud']['dt_com_nodes']
assert len(nodes) == 1 and nodes[0]['status'].strip('\0') == 'disabled'
plan = {
    'scope': 'minimal boot-off-only route supplier plan, not kernel implementation',
    'recommendation': 'explicit early/probe EUD producer admission plus trusted structured BeforeEBS completion record; memory-only revocable supplier',
    'files': files,
    'source_identity': 'cached ba61 Image363 functions retained by Image501 except the independently bound gauge leaf',
    'DT_source_limit': 'source354 snapshot COM okay is historical; current exact native DTB9271 and retained postboot04 COM disabled are separate facts',
    'native_DTB_sha256': '9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358',
    'current_COM_disabled': True,
    'claim_limit': 'primary region claim does block current new COM/full-EUD probes before AHB/SCM; earlycon and non-requested MMIO are outside it',
    'bus_notifier_veto_proven': False,
    'missing_exact_driver_core_resource_callers_not_fetched_or_mounted': True,
    'firmware_producer': 'actual SamuraiEudBeforeExitBootServices, only successful full-word afterCSR0 can publish valid',
    'firmware_current_gap': 'only private static handoff structure/DEBUG log; no structured trusted Linux completion record or EudLog timer join',
    'earlycon_order': 'boot-off opt-in denies first early CSR/FIFO access before later supplier parsing; any prior producer_seen refuses this boot',
    'token_scope': 'exclusion of audited EUD software producers, no inferred PD/PHY/role/native-current/APSD permission',
    'revocation': 'mark blocked and increment generation under short supplier lock, pin client, unlock cancel_join, put; failed join retains tombstone',
    'unknown_reset_retention_revokes_without_auto_regrant': True,
    'route_granted': False, 'APSD_enabled': False, 'kernel_code_written': False,
    'device_SDK_build_mount_shared_source_Git_operations': False,
    'plan_readme_sha256': sha(HERE / 'README.md')
}
(HERE / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
print(json.dumps({'plan_sha256': sha(HERE / 'plan.json'), 'kernel_implementation': False, 'route_granted': False}))
