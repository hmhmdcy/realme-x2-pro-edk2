"""New RAM-capture namespace; retain the current236 boot guard and rollback."""
from pathlib import Path
import json

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel237')
assert not P.exists()
P.mkdir(mode=0o700)
(P / 'usb-ipv6-candidates-private.json').write_bytes((P.parent / 'kernel236/usb-ipv6-candidates-private.json').read_bytes())
source = (R.parent / 'kernel236/host.py').read_text().replace('kernel236', 'kernel237').replace('usb236', 'usb237').replace('Authenticated236', 'Authenticated237').replace('current boot233', 'current boot236')
(R / 'host.py').write_text(source)
archive = ROOT / 'archive/NEXT-SESSION-through236-2026-10-16.md'
assert not archive.exists()
archive.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
(P / 'current-work-private.json').write_text(json.dumps(dict(stage=237, guard='/var/lib/samurai/k236-runtime/boot-id-private.txt',
 state='prepared, fresh baseline pending', active_native_context=None, transition_pending=False,
 previous_goal_turn_classification='progress', full_peripheral_goal_active=True,
 next='Fresh236 baseline, build exact physical camera selector then finite rear RAW capture with complete recovery'), indent=2) + '\n')
(ROOT / 'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-16，237进行中；上一轮236是progress。当前仍236启动，后摄IMX319真实ID0319/挂起/P两路OFF和libcamera双摄枚举通过，尚无后摄帧。完整goal active。

## 当前状态

新运输reference/kernel237/host.py，私人237/current-work-private.json记录当前worker。guard仍/var/lib/samurai/k236-runtime/boot-id-private.txt；全部233及更早guard失效。无重启/刷写计划。完整当前组件、回退、实际失败、蓝牙当前开启1连接只观察、GNSS零CNR等见[236检查点](archive/NEXT-SESSION-through236-2026-10-16.md)及[236](reference/kernel236/README.md)。边界见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。

## 源码、产物与回退依据

当前boot235/MFD6021/lab5198/provider2223/imx319176f、前摄e49/CAMSSfae1/FastRPC2abd保持；真正当前模块清单为设备k236-lab-fix/module-inventory-after-private.json。235/236冻结源与私人备份保留；canonical仍after228，不能刷其旧相机输出。当前lab已绑定有消费者，不可重放236未绑定/ref0卸换脚本。无NV/校准/工厂备份写入。

## 续作与已知风险

237新探针需同时匹配exact OF camera ID、Model和真实sensor subdev；旧219/233硬编码前摄CCI1，不能用于后摄。先IMX3191632x1224真实RAW六帧RAM统计，记录SOF时间戳，FrameSuccess才计帧；不存/显示场景、不闪光、不加照明。逐项尽力清理并记录失败，恢复全图/格式/两sensor控制，确认P/Q rails和时钟/PM，成功后做前摄回归。禁止因观察超时重启同一worker；先核terminal或实际进程。GNSS及其它完整适配仍开放，研究见[同平台方案](reference/kernel236/RELATED-LINUX-SOLUTIONS.md)。
''')
print(json.dumps(dict(stage=237, namespace_prepared=True, previous_goal_turn='progress', phone_not_yet_contacted=True)))
