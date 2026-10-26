from pathlib import Path
import ast
import hashlib
import json
import shutil

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel145'
out = Path('/mnt/e/edk2-samurai-out/kernel145')
kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
build = json.loads((ref / 'build-validation.json').read_text())
tests = json.loads((ref / 'actual-function-test-validation.json').read_text())
previous = json.loads((root / 'reference/kernel144/build-validation.json').read_text())
cleanup = json.loads((ref / 'cleanup-validation.json').read_text(encoding='utf-8-sig'))
ledger = json.loads(Path('/mnt/e/edk2-samurai-out/cleanup145/cleanup-ledger-private.json').read_text(encoding='utf-8-sig'))
assert build['image_modules_dtb_build_completed'] and previous['image_modules_dtb_build_completed']
assert tests['candidate_cases'] == 24 and tests['baseline_candidate_hardware_effect_signatures_identical']
assert cleanup['complete'] and ledger['complete'] and not cleanup['phone_modified']
assert cleanup['removed_candidate_files'] == 98 and cleanup['duplicate_iso_chunks_removed'] == 8
assert len(ledger['archived_volumes']) == 5
assert all(row['verified'] and row['source_removed'] for row in ledger['archived_volumes'])
assert all(row['removed'] for row in ledger['removed']) and len(ledger['removed']) == 106
assert not build['deployed'] and not build['goal_complete']


def digest(path):
    state = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            state.update(block)
    return state.hexdigest()


assert digest(kernel / 'arch/arm64/boot/Image') == build['files']['Image-k145-dsi-observation-private']['sha256']
assert digest(kernel / 'drivers/gpu/drm/msm/dsi/dsi_host.c') == build['source_sha256']
assert digest(kernel / 'drivers/gpu/drm/msm/msm_dsi_trace.h') == build['trace_header_sha256']
assert digest(kernel / 'drivers/tty/serial/eud.c') == previous['source_sha256']
assert digest(kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb') == build['files']['sm8150-samurai-k145-private.dtb']['sha256']
for row in ledger['archived_volumes']:
    source = Path('/mnt/e') / row['source'][3:].replace('\\', '/')
    archive = Path('/mnt/e') / row['archive'][3:].replace('\\', '/')
    assert not source.exists() and archive.is_file() and archive.stat().st_size == row['archive_bytes']

freed_gib = cleanup['free_bytes_increased'] / 1024**3
free_gib = cleanup['free_bytes_after'] / 1024**3
summary = (
    '阶段145：144重启回执补丁已恢复完整构建；145新增DSI原始错误、IRQ和复位边界追踪，'
    '24项实际函数宿主测试通过且硬件操作顺序与144一致，Image/modules/DTB完整构建通过。'
    '当前构建源码与Image均为145，手机仍为回退140/software132，145未部署。'
    f'按用户要求清理E盘98个过时产物、8个核对一致的下载分片，5个旧构建卷压缩并验证后封存，'
    f'可用空间增加{freed_gib:.2f}GiB，结束时剩余{free_gib:.2f}GiB。'
    '显示、GPU迟发CCU及充电控制保护均未验收，goal active。'
)
session = '''# 阶段145：DSI追踪构建与E盘旧产物清理

2026-10-12，显示、GPU、充电完整适配目标继续 active。

''' + summary + '''

## 构建恢复与现有补丁

144此前完整链接中断、残留Image143的状态已经结束。仅清理已确认的零字节链接中间产物，使用降低内存需求的链接选项、两路构建和单进程3GiB地址空间上限后，144 Image/modules/DTB全部构建通过。未修改全局交换设置、内核配置或原C盘WSL虚拟磁盘。144原有26项实际EUD函数测试通过；真实主机收到重启F1、实机panic仍待验证。

145仅在DSI host增加追踪点并新增追踪头文件，139 SLIMbus回收、140 DMA诊断、144 EUD退出同步、GPU与充电实现均保持。使用原有寄存器读取值，追踪IRQ、六类原始错误以及worker复位前后边界，未新增MMIO读写、printk、延时或锁。旧ACK错误聚合标志为0，145保留其行为并记录原始ACK值；这解释了现有聚合状态可能丢失的信息，不构成显示根因结论。

9个实际驱动函数直接抽取，24项用例覆盖原始零值/非零值/未知位、ACK聚合为0、FIFO欠载、worker复位、IRQ与完成次序。144基线与145候选在普通编译及ASAN/UBSAN下通过，硬件操作签名一致。模型的MMIO及未改动的复位/中断辅助函数是替身，不能证明实机时序或显示验收。

145 checkpatch及DSI对象W=1均无报错/警告；Image/modules/DTB完整构建成功，770个模块对象和三个追踪点符号已核验。DTB与132相同。工作树源码与Image均145，private out保留145 Image/DTB/System.map。尚未安装145模块、生成完整刷机包、部署145或建立新实机recorder。不要重放145一次性应用/构建脚本；以build-validation.json及私有产物校验为准。

## E盘清理范围与恢复

仅操作E:\\edk2-samurai-out中的明确旧产物。移除98个旧候选镜像/模块/根文件系统导出；8个下载分片逐字节连接的SHA256与保留完整EWDK ISO一致后删除。完整ISO仍保留。

kernel118、122、126、129、134的5个未挂载旧构建卷均完整压缩为zstd封存，逐个解压流的长度与SHA256和原文件一致后才移除原卷。历史源码、配置与卷内记录仍可完整还原。封存位于私有cleanup145/volumes，原始路径、SHA256、压缩长度和动作收据保存在cleanup-ledger-private.json。不得直接运行旧ensure/mount脚本以创建空卷；确有需要时先从封存恢复对应原卷并核对私有ledger中的长度与SHA256。当前构建树在原C盘WSL文件系统，不依赖这5个旧卷。

保留132启动镜像、模块和根文件系统，140当前回滚Image/logdump、145候选Image，以及原始日志、补丁、源文件、工厂/NV/分区备份。受保护产物清理前后SHA256一致，手机未改动。此前为恢复构建迁往C盘的拒收134根文件系统导出仍按私有144 relocation记录保留；本次仅清理E盘。

日期JSON转换曾触发清理前停止，当时ledger零删除/零归档。核对98项未发生变化，修正为UTC ticks比较并保留失败ledger后开始清理。完成98项删除后，下载分片目录笔误触发第二次停止，尚未删除分片或归档旧卷；按组装记录纠正为ewdk-download目录，并保存该阶段ledger。续跑只在核对98项已删除且路径与清单一致后跳过删除阶段。清理脚本已经终态，不得重新执行；私有ledger逐项记录结果。

## 手机状态与下一步

手机仍#140/software132，身份只用私有kernel143/embedded-boot-id-private.txt或phone k143-rollback140-runtime。既有144只读快照DPU0/DSI0/GPU0/WARN0、TXprepare9、taint0，显示自动空闲。空闲无报错不能代替显示/GPU/充电专项验收。本轮清理没有新手机观测。

显示下一步是建立新的145打包与实机实验守卫，核验145模块安装树和132系统兼容性后，关联DSI原始FIFO状态、IRQ/复位边界及现有DPU kickoff/完成事件。保留83ms看门狗和MMIO节奏，不能凭调高时钟/延长超时或聚合status=c宣布修复。143全部停止、切换、A/B、recorder和回退动作均终态，禁止重放；145现场动作必须使用新路径和本次状态守卫。

GPU136两次迟发CCU故障仍开放，gpu_probe_allowed=false；提交时刻、同一VM映射和BO/CCU关系未闭合，画面正确或日常桌面提交不算专项验收。禁止旧33矩阵、全局debug或全局缓存刷新。充电138的寄存器读取、终止/恢复阈值是已验证证据，持续输入/温度/保护/失联与控制验收仍待办，不能把低电流直接当作控制失败或成功。

禁止全刷userdata、NV/GPT/工厂备份操作、提交推送、BT配对、振动新增脉冲、FET/OTG/OTP/unseal写入。私有原始日志、身份、地址与镜像不公开。144资料中的“Image143残留/144未构建”是历史事件，已由本阶段成功构建结果替代；相应历史记录保留。
'''
target = root / 'sessions/145-dsi-observation-and-old-build-cleanup.md'
assert not target.exists()
backup = out / 'docs-before-private'
assert not backup.exists()
backup.mkdir()
names = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'README.md',
         'linux-port/README.md', 'linux-port/docs/HARDWARE-STATUS.md',
         'DOCS-INDEX.md', 'HANDOVER-NEXT.md']
for name in names:
    shutil.copyfile(root / name, backup / name.replace('/', '--'))
shutil.copyfile(ref / 'source-validation.json', out / 'source-validation-before-checkpoint-private.json')
source = json.loads((ref / 'source-validation.json').read_text())
assert source['candidate_source_sha256'] == build['source_sha256']
source['built'] = True
(ref / 'source-validation.json').write_text(json.dumps(source, indent=2) + '\n')
target.write_text(session)
next_text = '''# Realme X2 Pro继续检查点（阶段145，2026-10-12）

''' + summary + '''

先读sessions/145-dsi-observation-and-old-build-cleanup.md，以及reference/kernel145的actual-function-test-validation.json、source-validation.json、build-validation.json与cleanup-validation.json。144重启修复已完整构建，145保留该修复并新增DSI追踪。

实际手机#140/software132，身份只用私有kernel143/embedded-boot-id-private.txt或phone k143-rollback140-runtime。WSL /home/cy122/pmos-samurai-kernel136/kernel现为源码145/Image145，名称136不是当前版本。145尚无完整刷机包和新模块安装树，未部署；143动作全部终态，禁止重放。

E盘清理已终态；98旧候选产物、8重复ISO分片移除，5旧构建卷完整压缩并核验。当前/回滚/工厂备份、源码和原始日志保留。历史E118/122/126/129/134原卷已封存，需要时先按私有cleanup145 ledger还原并校验，禁止直接执行旧ensure创建空卷。原C盘WSL及当前145源码/构建均保持。

下一步准备新的145实机实验与守卫，关联DSI原始错误和DPU帧时序；GPU136迟发CCU与充电控制保护继续待办。保持83ms看门狗与原MMIO节奏、gpu_probe_allowed=false、不全刷userdata、不提交推送、BT不配对、振动不新增脉冲、不写FET/OTG/OTP/unseal、不公开私人材料，goal active。
'''
(root / 'NEXT-SESSION.md').write_text(next_text)
(root / 'NEXT-SESSION-PROMPT.md').write_text('# 下一会话短提示词\n\n' + next_text.split('\n\n', 1)[1])
for name, link in [('README.md', 'sessions/145-dsi-observation-and-old-build-cleanup.md'),
                   ('linux-port/README.md', '../sessions/145-dsi-observation-and-old-build-cleanup.md'),
                   ('linux-port/docs/HARDWARE-STATUS.md', '../../sessions/145-dsi-observation-and-old-build-cleanup.md')]:
    path = root / name
    head, rest = path.read_text().split('\n', 1)
    path.write_text(head + '\n\n最新阶段145：' + summary + '\n\n详见[阶段145](' + link + ')。以下为此前历史。\n' + rest)
path = root / 'DOCS-INDEX.md'
head, rest = path.read_text().split('\n', 1)
path.write_text(head + '\n\n- [阶段145：DSI追踪构建与E盘旧产物清理](sessions/145-dsi-observation-and-old-build-cleanup.md)\n' + rest)
path = root / 'HANDOVER-NEXT.md'
head, rest = path.read_text().split('\n', 1)
path.write_text(head + '\n\n当前以[NEXT-SESSION](NEXT-SESSION.md)及[阶段145](sessions/145-dsi-observation-and-old-build-cleanup.md)为准：手机140，源码/Image145，完整构建通过但未部署；旧E盘构建卷已压缩封存。下方为旧历史。\n' + rest)
for path in ref.glob('*.py'):
    ast.parse(path.read_text())
assert '阶段145' in (root / 'NEXT-SESSION.md').read_text()
assert '完整构建通过但未部署' in (root / 'HANDOVER-NEXT.md').read_text()
(ref / 'documentation-validation.json').write_text(json.dumps(dict(
    stage=145, current_phone_kernel=140, current_source_stage=145, current_image_stage=145,
    kernel_build_completed=True, deployed=False, cleanup_completed=True,
    latest_documents_updated=True, python_syntax_pass=True,
    historical_archived_volumes_require_verified_restore=True, goal_complete=False), indent=2) + '\n')
print('K145_CHECKPOINT_SOURCE145_IMAGE145_PHONE140_CLEANUP_COMPLETE_GOAL_ACTIVE')
