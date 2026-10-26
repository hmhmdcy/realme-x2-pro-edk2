"""Record actual234 partial experiment, restored runtime and next implementation."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import subprocess

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel234')
health = json.loads((R / 'final-health-validation.json').read_text())
analysis = json.loads((R / 'diagnostic-analysis-validation.json').read_text())
evidence = json.loads((R / 'evidence-validation.json').read_text())
assert health['taint'] == 0 and not any(health['fault_counts'].values())
assert analysis['actual_phase5_records_correlated'] == 2 and analysis['scan_not_completed']
assert evidence['all_members_verified'] and evidence['native_members'] == 58
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
assert helper.snapshot() == json.loads((P.parent / 'kernel228/canonical-after-private.json').read_text())
archive = ROOT / 'archive/NEXT-SESSION-through233-2026-10-16.md'
if archive.exists():
    assert archive.read_bytes() == (ROOT / 'NEXT-SESSION.md').read_bytes()
else:
    archive.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
text = '''# Realme X2 Pro 当前检查点

2026-10-16，234：RTS/H4模型已执行，取得两次完整切速回包/零跟踪丢失；扫描脚本Not Powered退出，原185模块/配置恢复、最终健康通过。后摄/GNSS未完成，goal active。[234](reference/kernel234/README.md)、[233归档](archive/NEXT-SESSION-through233-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 仍为233启动，guard /var/lib/samurai/k233-runtime/boot-id-private.txt；所有更早guard失效。运输reference/kernel234/host.py沿原SSH公钥/USB scoped endpoint。私人234/current-work-private.json为续作指针。无活动worker/切换/构建/捕获，两轮跟踪实例均删除，桌面/WP/音频保持。
- boot232 45f398f2…/100663296B、DTB7e8345ae…，Image183 bfa72dd9…/logdump183 e73754c7…；234未刷分区/重启。新MFD f633467f…/20520B、provider2223f337…/9744B实际加载note正确/intreeY，options experimental_p_address_only=1、softdep provider先加载。P1-0008/Q1-0004/provider绑定；P身份0x0100正确，无secondary/MFD/regulator children，P未写VIN/供电。
- 233原生Q暖循环保持七路状态/电压，provider冷循环一次Q8→4迁址/P身份恢复；GPIO为软件trace，非pad测量。Q七路关/users0，前摄及CCI/CAMSS suspended，详见233归档。
- 前摄e49dab26…/29536B、CAMSS fae1ed40…/777360B、libcamera99990.7.2-r13/config0.1.0-r8。233冷循环后RAW/RGB各6帧非零，仅RAM统计/不存照片/不加照明。用户延期纯色参照，不再追问、不称颜色准确/AE收敛；图案0/fullres=N/前摄双轨关。完整模式和颜色/几何/GUI性能待验。
- 773ko/787相关文件、944包保持。FastRPC默认/运行2abde0ea…/50192B/intreeY/ref1；taint0/模块taint空，WARN/Oops/GPU/DSP fatal/BT重组0。三DSP running、SensorProxy三Has真；233加速度/光线readiness通过，230完整五流为旧boot证据。
- Wi-Fi connected、chrony Normal；GPS Enabled0/Signalsfalse/rate30、watch空闲/timeprepared/data worker0。本轮没启GNSS/注入，226四轮零CNR/168h XTRA为旧boot证据。MM191 b350c55b… State−1/原因2/Power1，用户无SIM；未验蜂窝业务。
- BT当前原185 f6c5ed35…默认和加载note匹配，无诊断参数；helper/BlueZ原配置/keys/787文件全恢复，蓝牙关/无连接。234普通初始化2个phase5 chunk各12B且H4完整结束，匹配UART；102.4MHz/div1/32配置3.2Mbps，命令到RX7.352/11.110ms，1301条GENI事件/零溢出丢失。未复现历史phase5，也未称修复。
- 234扫描未完成：预上电布尔属性loop返回Not Powered，具体属性未记；worker exit1/failed、cleanup0、最终健康0/58成员核验。第一次baseline路径错误/r2更正证据保留，不称本轮全部通过。

## 源码、产物与回退依据

- canonical /home/cy122/pmos-samurai-kernel136/kernel保持after228，FastRPC f378afed…整合/16798符号/772全局顺序。相机canonical仍旧216 IMX/旧CAMSS，不刷整套Image/DTB。当前相机源锁在camera/kernel、225，完整FastRPC在ssc/kernel。
- PMIC完整源/补丁/两板源/片段/source-lock在linux-port/camera/pmic，MFD源bd6c578e…/provider b0e46fad…。树内W=1、97实际函数ASan/UBSan/3负对照及233暖/冷循环；不称完整新内核/rootfs/schema通过，构建CONFIG_RESET_REALME_RMX1931_PM8008=m。
- boot232候选私人232/boot-partition-k232-pmic-identity.img；219回退156f0370…/96MiB在私人219/boot-partition-k219-front-modes.img。旧MFD d1ff82c0…/14336B在设备k233-baseline及k233-module-stage，14元数据在k233-baseline/module-metadata-before；新loader配置此前不存在。回退先核当前身份、恢复文件/配置/元数据再正常重启，不热卸有children模块。其它回退见233归档。
- 234诊断完整源/补丁在reference/kernel234，源390611b0…/模块8bfb059f…/141704B仅临时加载，默认关/phase5/每open16chunk×32B，解析行为不变。W=1零诊断/intreeY/匹配183ABI；canonical/蓝牙对象恢复，第一构建及采样修正保留，未部署GENI功能补丁。
- 234修复205缺TIOCM_LOOP编译错误，实际C模型三变体ASan/UBSan为16/2、16/0、16/2；旧205失败原样保留。锁为stub，不证明并发正确，裸末尾同步不满足真实端口锁/IRQ契约；需避开console/RS485。真实H4函数8例通过，partial0可有skb，chunk头不等于错误offset，不吞FF/补04。
- GENI源5bb9ba5e…与base一致，ELF→保留183 Image的set_mctrl436B/termios964B逐字匹配、无直接BL同步；不是读取live指令。私人233/234原生成员158/58均核验，无场景像素/无公开私有标识。镜像233已8550文件/三项检查0；234以私人最终镜像收据为准。

## 续作与已知风险

优先实现真实IMX319 OF/runtime及P严格两路profile；226/227只是设计。只L1P1.104V/L4P2.8V、掩码0x09，其余五路在读/注册前跳过，L7P是指纹3.3V。P PLDO父网未知不编造；OEM/stock另声明P NLDO→S8C，不等于233已连接，真实父票须核固定约束。VSET写前关断/写后双字节核对，I2C错误锁存fault；global0x0950 bit0置前七路全关；enable写失败也清本路，READY回滚在.enable内部，disable失败不清状态flag。无法确认off则停止重试，sensor→child→P MFD退出、P-only reset回收，Q保持暖。

IMX319两家global136/mode171逐条相同；已有完整XML只IMX471。下一可沿217分析副本导出IMX319完整XML/核171寄存器，再新增OF三真实supply/reset/MCLK/PM及OEM1632×1224模式，保留ACPI。177.6MHz元数据不能直接作阵列时序；LLP2080/FLL3350与30fps需独立VT/OP核验，link222MHz/VT209.066667MHz仅推导。详见234/RESEARCH-FOLLOWUP。

BT不重复堆未复现扫描。改GENI先扩展锁/RS485/console/PM/serdev模型和独立内核候选，不刷canonical旧camera整套。预上电属性脚本错误保留，无需补次数。

GNSS无正CNR/TRACK/fix。R GPL MEMSHARE52/v1/instance1、GPS client0是新差异，但DTS size0/无MPSS请求证据，不认定根因。QRTR trace不含lookup服务参数，下一仅观察真实请求，无需户外、不注册伪服务/盲分配。231及RF GPIO/SMEM未形成缺口；82第三方来源纠正、226基础DTB来源未知仍在。

其余摄像头/GPU/传感器/PM/音频/充电/指纹/NFC/rootfs整合开放项见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。三路只读研究授权保持，手机串行，不能局部通过即完成全goal。
'''
assert len(text.encode()) <= 6500, len(text.encode())
(ROOT / 'NEXT-SESSION.md').write_text(text)
status = ROOT / 'linux-port/docs/HARDWARE-STATUS.md'
s = status.read_text()
start = s.index('用途：')
end = s.index('\n\n', start)
s = s[:start] + '用途：当前硬件验收清单。最后核对2026-10-16，234。233 PMIC部署/暖冷循环及前摄RAW/RGB保持；234蓝牙模型和H4回放通过、实得2次切速轨迹，扫描脚本Not Powered退出后原185模块/配置已恢复，最终健康0。后摄尚未出图、GNSS无正CNR，完整goal active。[234](../../reference/kernel234/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。' + s[end:]
old = '| 蓝牙 | 205两次普通启动'
assert old in s
s = s.replace(old, '| 蓝牙 | 234实际RTS模型三变体16/2、16/0、16/2及H4回放8例通过；暂时诊断取得2个完整phase5回包/UART对应/1301事件无丢失，未复现错误。扫描因预上电属性Not Powered未完成，已恢复原185模块/config/helper/keys/787文件、最终健康0；裸RTS模型不满足真实锁契约，未部署功能补丁。[234](../../reference/kernel234/README.md)。205两次普通启动')
status.write_text(s)
session = ROOT / 'sessions/234-bt-rx-state-and-uart-artifact-evidence.md'
session.write_text('# 234 蓝牙帧状态诊断与串口产物核对\n\n2026-10-16。前摄纯色测试按用户延期，继续其他适配。实际模型与H4回放通过，临时诊断得到两次完整切速记录；扫描脚本失败和原模块/配置恢复均保留，未宣称phase5修复。当前仍233启动、后摄及GNSS开放。\n\n详见[结果与限制](../reference/kernel234/README.md)、[原生摘要](../reference/kernel234/diagnostic-native-validation.json)、[最后健康](../reference/kernel234/final-health-validation.json)、[下一实现依据](../reference/kernel234/RESEARCH-FOLLOWUP.md)。\n')
for stage in [230, 231, 232, 233, 234]:
    path = P.parent / ('kernel' + str(stage)) / 'current-work-private.json'
    data = json.loads(path.read_text())
    data.update(next='Continue from private234/current-work-private.json and root checkpoint. Runtime233 guard; 234 BT trace acquired and185 restored. Next real IMX319 OF/runtime and strict P L1/L4 implementation, not repeated no-error BT loops.',
                full_peripheral_goal_active=True, front_known_colour_test_deferred_by_user=True)
    if stage == 234:
        data.update(state='234 BT models/H4 replay done, two native phase5 captures acquired; scan harness failed Not Powered; original185 and configs restored, final health clean',
                    active_native_worker=None, active_build_session=None, active_mirror_session=None,
                    active_evidence_session=None, runtime_guard='/var/lib/samurai/k233-runtime/boot-id-private.txt',
                    native_members=58, native_experiment_exit_code=1, native_cleanup_errors=[],
                    final_health_exit_code=0, previous_goal_turn_classification='progress', transition_pending=False)
    path.write_text(json.dumps(data, indent=2) + '\n')
subprocess.run(['python3', str(ROOT / 'linux-port/scripts/generate-session-index.py')], check=True)
for p in R.glob('*.py'):
    ast.parse(p.read_text())
lock = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in R.iterdir()
        if p.suffix in ['.py', '.c', '.patch', '.md']}
(R / 'source-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
report = dict(stage=234, python_syntax_files=len(list(R.glob('*.py'))),
              checkpoint_bytes=len((ROOT / 'NEXT-SESSION.md').read_bytes()),
              canonical_after228_preserved=True, native_members=58,
              original_bluetooth_restored=True, scan_failure_preserved=True,
              final_health_clean=True, full_peripheral_goal_active=True)
(R / 'source-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
