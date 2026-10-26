"""Close the implemented/staged milestone without claiming candidate hardware."""
from pathlib import Path
import ast
import difflib
import hashlib
import importlib.util
import json
import subprocess

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel235')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for filename in ['pmic-build-validation.json', 'imx319-build-validation.json']:
    report = json.loads((R / filename).read_text())
    for name, digest in report['source_inputs'].items():
        assert sha(R / name) == digest
health = json.loads((R / 'final-health-validation.json').read_text())
evidence = json.loads((R / 'evidence-validation.json').read_text())
assert health['taint'] == 0 and not any(health['fault_counts'].values()) and evidence['all_members_verified']
assert json.loads((R / 'lab-fault-validation.json').read_text())['source_sha256'] == sha(R / 'qcom-pm8008-imx319-lab.c')
assert json.loads((R / 'imx319-fault-validation.json').read_text())['source_sha256'] == sha(R / 'imx319.c')
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
assert helper.snapshot() == json.loads((P.parent / 'kernel228/canonical-after-private.json').read_text())
old = (R.parent / 'kernel232/qcom-pm8008.c').read_text()
new = (R / 'qcom-pm8008.c').read_text()
(P / 'pmic-source-initial-validation-private.json').write_bytes((R / 'pmic-source-validation.json').read_bytes())
(P / 'pmic-initial-diff-private.patch').write_bytes((R / 'pm8008-p-imx319-lab.patch').read_bytes())
(R / 'pm8008-p-imx319-lab.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
    fromfile='a/drivers/mfd/qcom-pm8008.c', tofile='b/drivers/mfd/qcom-pm8008.c')))
source = dict(stage=235, canonical_after228_preserved=True,
    mfd_before_sha256=hashlib.sha256(old.encode()).hexdigest(), mfd_candidate_sha256=sha(R / 'qcom-pm8008.c'),
    regulator_candidate_sha256=sha(R / 'qcom-pm8008-imx319-lab.c'), shared_header_sha256=sha(R / 'qcom-pm8008-imx319-lab.h'),
    q_regulator_source_unchanged=True, new_profile_default_disabled=True, profiles_mutually_exclusive=True,
    fault_lifetime_is_parent_mfd_epoch=True, physical_p_vin_unmanaged_and_not_invented=True,
    p_reset_fallback_is_isolation_not_register_restoration=True, independent_reset_failure_risk_retained=True,
    candidate_runtime_not_loaded=True, module_files_staged=True)
(R / 'pmic-source-validation.json').write_text(json.dumps(source, indent=2) + '\n')
archive = ROOT / 'archive/NEXT-SESSION-through234-2026-10-16.md'
assert not archive.exists()
archive.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
text = '''# Realme X2 Pro 当前检查点

2026-10-16，235：真实IMX319 OF/runtime与P严格两路供电已实现/编译，候选boot已构建，三个模块已原子暂存；尚未加载候选、未读新后摄ID/出帧。仍233启动。完整goal active。[235](reference/kernel235/README.md)、[234归档](archive/NEXT-SESSION-through234-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- guard仍/var/lib/samurai/k233-runtime/boot-id-private.txt，235-baseline与其同boot；更早guard失效。运输reference/kernel235/host.py、私人235/current-work-private.json为续作指针。无活动worker/构建/切换/捕获。235未重启/刷分区/热卸PMIC，桌面/WP/音频保持。
- 运行boot232 45f398f2…/100663296B、DTB7e8345ae…、Image183 bfa72dd9…/logdump183 e73754c7…。运行MFD仍f633467f…/20520B、provider2223f337…/9744B；experimental_p_address_only=Y。P1-0008/Q1-0004/provider绑定，P身份已确认且仍无secondary/children/供电。
- 磁盘已暂存235：MFD6021a359…/22208B替换、lab22c28914…/17640B和IMX319 176f68d7…/36624B新增；775ko/789相关文件，kmod顺序及两种alias通过。配置已改experimental_p_imx319_power=1+原provider softdep，运行仍旧值；不可称默认/加载note相同。module-stage transaction verified，备份/元数据/原配置在设备k235-module-stage。
- 暂存后健康通过：taint0/模块taint空，WARN/Oops/GPU/DSP fatal/BT重组0；三个DSP running、SensorProxy三Has真，原FastRPC/前摄/CAMSS/BT/provider加载note匹配。P无secondary，前摄/CCI/CAMSS suspended，原分区读回不变。私有原生收据全成员核验；无场景像素。
- 前摄仍e49dab26…/29536B、CAMSS fae1ed40…/777360B，libcamera99990.7.2-r13/config0.1.0-r8；233冷循环后RAW/RGB各6帧有效是旧证据。纯色参照按用户延期，不再追问，不称色准/AE已验。图案0/fullresN，双轨关。FastRPC运行2abde0ea…/50192B/intreeY/ref1；944包保持。
- BT仍原185 f6c5ed35…/默认与加载note匹配，helper/config/keys保持、关/无连接。234两次完整phase5轨迹未复现错误，扫描脚本Not Powered退出后恢复；不是phase5修复。GNSS仍idle/无正CNR/TRACK/fix，室内窗边，无新注入/搜星。MM191无SIM/State−1原因2；真实蜂窝业务未验。

## 源码、产物与回退依据

- 完整235候选源/补丁/表/板片段/接入片段/构建及实际C故障测试在reference/kernel235。当前接受的旧232实验PMIC完整源仍linux-port/camera/pmic，235未冒作已验收。canonical /home/cy122/pmos-samurai-kernel136/kernel精确after228，16798符号/772全局顺序；相机仍旧216/旧CAMSS，不能刷整体Image/DTB。
- PMIC源99505695…/lab ce5c15bc…/header bccdd023…；树内W=1零诊断/intreeY/183 ABI，原Q及所有构建元数据恢复。465实际回调ASan/UBSan、3负对照；MFD40例/2负对照通过。故障属于父epoch；仅L1P1.104V/L4P2.8V/mask9，无假VIN。独立P assert+status成功才隔离/允许core平衡引用；失败不伪报OFF/不重复reset，仍有未回收引用/退出WARN风险。隔离不是寄存器恢复/电压实测。
- IMX319源ec1a278d…/header f366aba9…；原ACPI8模式表保持，OF三真实supply/managed child依赖/PM/checked GPIO+pinctrl。370实际power/identify/table/stream函数ASan/UBSan和4负对照通过，308配置写失败位置均测；ID失败/错ID零sensor写。模型不证明真实并发/devres/硬件。
- 两家独立vendor XML的global136/mode171完全一致，原BIN/payload保持。1632×1224 RAW10/RGGB/4lane、LLP2080/FLL3350、HBLANK448/VBLANK2126。177.6M元数据不自洽；link222M/VT209066666仅推导，须SOF测。原机CCI0/master1/0x10、MCLK1/GPIO14/19.2M、reset30、CSIPHY1；MCLK active/sleep6mA、reset2mA/sleep低，不复制前摄。
- DTB469e1456…/112137B相对真实232仅12新节点和3属性变化；camcc/TITAN_TOP/MCLK/供电/双向lane graph phandle全核对。boot235 44c6a215…/96MiB，私人235/boot-partition-k235-imx319-p-lab.img；解包仅内嵌FDT变化、固件代码/头/ramdisk/兼容DTB/尾及183 Image保持，30条既有固件诊断无新模板，不称完整kernel/rootfs/schema完成。
- 当前232 boot回退45f3在私人232/boot-partition-k232-pmic-identity.img；219回退156f0370…仍私人219。235回退先核新身份，恢复k235-module-stage/before中MFD和14元数据、原配置，移除精确两个新增module路径，再正常重启/必要时只刷已锁232 boot。不能热卸有children的MFD，不触NV/校准/工厂备份。锁在私人235/deployment-lock-private.json。

## 续作与已知风险

下一步直接准备新的受控过渡/原生验收，不再重复XML/已过host矩阵。当前磁盘与运行MFD不同，旧233/234默认清单已不适用；以235-module-stage清单核磁盘、以before note核运行。新清理工具需保留运行P/Q/provider，仅清相机端点；不能套233的provider未加载断言。新身份/几何后仅flash锁定235 boot一次，未明切换不重发；新boot建立新guard再核775/789、加载note/P两路/后摄ID/自动挂起，然后有界RAW RAM统计、回收及前摄回归。不保存照片/不加照明。

首次DTB校验把标签误当regulator-name，r1编译成功/检查退出；r2按前摄真实vif phandle核对通过。所有早期构建/模型失败私有保留。已执行脚本一次性目录/旧guard不能重放。235最终镜像/成员数以私人收据和source-final为准。

GNSS研究纠正：本树QRTR NS只接受本地lookup观察者，MPSS可在自身NS等公告；AP没看见52 lookup不能排除MEMSHARE需求，qrtr-lookup不能证明固件请求，现trace无服务参数。不要为此单独刷内核/伪服务/盲分配。继续真正RF/OEM差异。BT不堆未复现扫描；GENI功能补丁仍须真实端口锁/IRQ/console/RS485/PM验证。

其余四后摄/前摄颜色几何/GPU ISP/传感器精度SSR/USB与Wi-Fi PM/音频/充电保护/指纹/NFC/rootfs等见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。三路只读研究授权保持，手机由root串行；不得以局部通过完成全goal。
'''
assert len(text.encode()) <= 6500, len(text.encode())
(ROOT / 'NEXT-SESSION.md').write_text(text)
status = ROOT / 'linux-port/docs/HARDWARE-STATUS.md'
s = status.read_text()
start, end = s.index('用途：'), s.index('\n\n', s.index('用途：'))
s = s[:start] + '用途：当前硬件验收清单。最后核对2026-10-16，235。真实IMX319 OF/runtime及P严格两路供电已实现、树内编译/故障模型通过，候选boot构建和三个模块磁盘暂存完成；当前仍233启动/232驱动，未加载235候选、未读新后摄ID/出帧。暂存后健康通过、taint/fault0；GNSS无正CNR，完整goal active。[235](../../reference/kernel235/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。' + s[end:]
s = s.replace('真实后摄供电/驱动待做', '235真实IMX319 OF/runtime/P严格L1-L4已实现、编译及模型通过并仅磁盘暂存；新启动ID/出帧待验')
status.write_text(s)
session = ROOT / 'sessions/235-imx319-of-runtime-and-isolated-p-power.md'
session.write_text('# 235 IMX319真实驱动与独立P两路供电候选\n\n2026-10-16。用户延期前摄纯色测试，转入真实后摄实现。两家vendor XML、完整OF/runtime、严格两路供电、故障回收模型及树内构建完成，设备树/启动包生成；模块已原子暂存，当前仍233启动，未加载候选或完成后摄出帧。\n\n详见[实现与证据限制](../reference/kernel235/README.md)、[暂存](../reference/kernel235/module-stage-validation.json)、[健康](../reference/kernel235/final-health-validation.json)、[检查点](../NEXT-SESSION.md)。\n')
camera = ROOT / 'linux-port/camera/README.md'
camera.write_text(camera.read_text() + '\n235新增真实IMX319 OF/runtime与P严格两路供电候选，已完成独立XML/构建/故障模型及磁盘暂存，尚未加载或验收后摄出帧。[候选及新启动步骤](../../reference/kernel235/README.md)。\n')
state_path = P / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='235 actual IMX319/P lab candidate built, three module files/options staged; current233/232 remains live; new hardware not yet tested',
             priority='Prepare fresh236 transition preserving live P/Q/provider, flash only locked235 boot once after fresh identity/geometry; new guard before ID/RAW/PM validation',
             next='Continue from private235/current-work-private.json and root checkpoint; do not rerun235 one-shot staging/export/build scripts',
             module_files_staged=True, hardware_candidate_loaded=False, transition_pending=False,
             active_native_worker=None, active_build_session=None, active_evidence_session=None,
             native_members=evidence['native_members'], previous_goal_turn_classification='progress',
             front_known_colour_test_deferred_by_user=True, full_peripheral_goal_active=True)
state_path.write_text(json.dumps(state, indent=2) + '\n')
for stage in [233, 234]:
    path = P.parent / ('kernel' + str(stage)) / 'current-work-private.json'
    data = json.loads(path.read_text())
    data.update(next='Superseded by private235/current-work-private.json/root checkpoint. Runtime233 guard remains; disk775ko/789 and235 options staged, live232 MFD retained. Old default manifests stale.')
    path.write_text(json.dumps(data, indent=2) + '\n')
subprocess.run(['python3', str(ROOT / 'linux-port/scripts/generate-session-index.py')], check=True)
for path in R.glob('*.py'):
    ast.parse(path.read_text())
lock = {path.name: sha(path) for path in R.iterdir() if path.suffix in ['.py', '.c', '.h', '.inc', '.dtsi', '.patch', '.md', '.fragment']}
(R / 'source-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
report = dict(stage=235, python_syntax_files=len(list(R.glob('*.py'))), checkpoint_bytes=len(text.encode()),
              canonical_after228_preserved=True, native_members=evidence['native_members'],
              candidate_runtime_not_loaded=True, disk_staging_health_passed=True,
              full_peripheral_goal_active=True)
(R / 'source-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
