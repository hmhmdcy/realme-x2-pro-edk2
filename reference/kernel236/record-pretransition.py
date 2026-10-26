from pathlib import Path
import json

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel236')
assert json.loads((R / 'baseline-validation.json').read_text())['current233_identity_verified']
assert json.loads((R / 'tools-validation.json').read_text())['exact_paths_hashes_syntax_verified']
archive = ROOT / 'archive/NEXT-SESSION-through235-2026-10-16.md'
assert not archive.exists()
archive.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
text = '''# Realme X2 Pro 当前检查点

2026-10-16，236切换工作进行中。235后摄候选已实现/编译/暂存；236新基线和9份精确路径工具校验通过。实际过渡阶段、活动worker和请求marker优先读私人236/current-work-private.json及原生状态；不能按旧交接重发操作。完整goal active。[235完整背景](archive/NEXT-SESSION-through235-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 切换前仍233启动，guard /var/lib/samurai/k233-runtime/boot-id-private.txt；新k236-baseline已与其当场核对，原k233-baseline属于更早boot，不能拿来核身份。运输reference/kernel236/host.py，严格原SSH公钥/USB scoped peer。
- 运行boot232 45f398f2…/96MiB、DTB7e8345ae…，Image183 bfa72dd9…/logdump183 e73754c7…。运行MFD232 f633467f…/20520B与provider2223f337…/9744B仍绑定P/Q，地址模式Y，无P secondary/children。
- 磁盘235三模块MFD6021a359…、lab22c28914…、IMX319 176f68d7…已暂存；775ko/789文件、experimental_p_imx319_power=1+provider softdep。运行与磁盘MFD不同。236新基线已核其全部清单、旧加载note、用户态/包/分区原清单、taint/fault0和三DSP/SensorProxy/BT状态。
- 9个切换/观察工具已上传并核路径、hash、Python/shell语法。只清四个相机端点模块，保留运行P/Q/provider；已修正旧233的provider未加载断言。新boot观察器将按OF路径找前/后摄，不能硬编码旧前摄7-0010；ID由真实probe比较0x0319后成功绑定证明。

## 源码、产物与回退依据

- 235完整驱动/严格L1P1.104V、L4P2.8V/mask9/故障锁存/P独立reset回收、原ACPI保持、XML136/171、875例实际C模型及9负对照、树内W=1/183ABI依据见235归档与reference/kernel235/README.md。不能当原生出帧验收；未知VIN和独立reset同时失败风险保留。
- 锁定235 boot44c6a215…/100663296B在私人235/boot-partition-k235-imx319-p-lab.img，DTB469e1456…；仅内嵌FDT变化，固件代码/183 Image/logdump保持。7产物锁已复制私人236/deployment-lock-private.json，回退键boot232_rollback为45f398f2…，另保留219回退156f0370…。绝不刷canonical整套旧相机输出。
- 设备k235-module-stage/before含旧MFD与14元数据、原配置另存；两个新增模块精确路径在235锁。回退须核当前身份、恢复文件/元数据/配置，正常重启；不热卸有children的MFD，不触NV/校准/工厂备份。
- canonical仍/home/cy122/pmos-samurai-kernel136/kernel after228；本轮只准备过渡，不构建/修改内核源。235私有原生55成员和镜像8639文件/检查0已完成，无场景像素；236收据后续另行归档。

## 续作与已知风险

先观察已有236 quiesce worker/终态；quiesce成功后执行一次Linux→bootloader，fresh fastboot身份/产品/几何后只刷锁定235 boot一次。未明切换不重复。新boot建立k236-runtime guard并核分区/789文件/默认与加载note/P两路/ID/自动挂起，再做有界RAW RAM统计和掉电回收/前摄回归。源、工具和native markers均为一次操作上下文，不盲目重放。

前摄纯色参照按用户延期，不再追问；不保存照片/不加照明。GNSS仍无正CNR/TRACK/fix，不能用AP看不见lookup52排除远端MEMSHARE需求；不伪服务/盲分配。BT历史phase5、其余后摄、无SIM蜂窝、精度/PM/SSR、GPU ISP等仍开放，见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。三路只读研究授权保持，手机由root串行，不能局部通过即完成全goal。
'''
assert len(text.encode()) <= 6500
(ROOT / 'NEXT-SESSION.md').write_text(text)
state_path = P / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='fresh baseline and9 tools passed; controlled quiesce is next',
             next='Run quiesce once, observe same native process; then guarded one bootloader request and only locked235 boot flash',
             archive235_checkpoint_saved=True, previous_goal_turn_classification='progress')
state_path.write_text(json.dumps(state, indent=2) + '\n')
old_state_path = P.parent / 'kernel235/current-work-private.json'
old = json.loads(old_state_path.read_text())
old['next'] = '236 transition in progress. Continue from private236/current-work-private.json and root checkpoint; do not replay235/233 actions.'
old_state_path.write_text(json.dumps(old, indent=2) + '\n')
print(json.dumps(dict(stage=236, pretransition_checkpoint_saved=True, checkpoint_bytes=len(text.encode()), no_transition_sent=True)))
