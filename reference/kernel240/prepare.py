"""Prepare local S5K3M5 adaptation; retain239 and all current runtime evidence."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel240')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
assert not P.exists()
P.mkdir(mode=0o700)
(P / 'usb-ipv6-candidates-private.json').write_bytes((P.parent / 'kernel239/usb-ipv6-candidates-private.json').read_bytes())
(R / 'host.py').write_text((R.parent / 'kernel239/host.py').read_text().replace('kernel239','kernel240').replace('usb239','usb240').replace('Authenticated239','Authenticated240'))
archive = ROOT / 'archive/NEXT-SESSION-through239-2026-10-16.md'
assert not archive.exists()
archive.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
source = K / 'drivers/media/i2c/s5k3m5.c'
(R / 's5k3m5-base.c').write_bytes(source.read_bytes())
(P / 'current-work-private.json').write_text(json.dumps(dict(stage=240,
    state='preparing S5K3M5 OEM19.2MHz driver and shared P power profile; fresh baseline pending',
    guard='/var/lib/samurai/k236-runtime/boot-id-private.txt', active_native_context=None,
    active_native_session=None, active_build_session=None, previous_goal_turn_classification='progress',
    full_peripheral_goal_active=True, installed_libcamera='r15', installed_config='r10',
    next='Authenticate boot236 and current r15 idle state; derive mode3 timing and strict P L2/L6 profile offline before build/deployment'),indent=2)+'\n')
(ROOT / 'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-16，240进行中；239为progress，r15/r10七包默认安装、实际首参同步两次start及前摄回归通过，后摄光学/全零帧、GNSSfix仍开放，goal active。[239完整归档](archive/NEXT-SESSION-through239-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前状态

运输reference/kernel240/host.py、私人240/current-work-private.json；仍应为236启动，guard /var/lib/samurai/k236-runtime/boot-id-private.txt，233及更早无效。240 fresh baseline待核；当前默认r15/r10，789模块权威k237清单。239各worker/构建/export已终态、清理/taint/fault0；没有刷写或重启待决。

## 源码、产物与回退依据

239全部证据/13包/原生153成员/ODM2文件保留，配方和部署锁已同步。r15源码/对象在libcamera214-root/work/libcamera239-r15-built，原214已恢复；canonical仍精确after228，旧相机输出不能整刷。当前lab有IMX319消费者，不得复演未绑定/ref0热卸；P/Q/provider保留。r15→r13/r8七包原生降级模拟通过，239事务与225实际七包可回退。各完整hash/boot/MFD/lab/模块回退依239归档。

## 续作与已知风险

240先适配S5K3M5：239原BIN双投影+有界decoder已核917init/212模式，保留延迟/重复/末WRITE8，无需重跑reader。按本机19.2MHz/CCI1master0 0x2d/reset23/MCLK3/CSIPHY3，优先2104x1560模式；PLL/VT/OP待复核。P现mask9 L1/L4，新增严格L2/L6 mask0x22及共享lease/复位隔离待实现，不猜VIN。三个已授权代理只读并行审时序、电源和GNSS配置采用链，手机主线程串行操作。仍只RAM场景统计、不存图/加光；前摄纯色按用户延期，后摄朝向可选问题未答。其余真实光学/GNSSfix/全机适配不缩减。
''')
print(json.dumps(dict(stage=240, previous_goal_turn_classification='progress',
    base_sensor_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    no_build_or_phone_operation=True)))
