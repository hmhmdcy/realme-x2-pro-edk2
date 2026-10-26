"""Verify sealed closeout evidence and write the current handover once."""
from pathlib import Path
import ast
import datetime as dt
import hashlib
import json
import re
import shutil
import tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel145'
out = Path('/mnt/e/edk2-samurai-out/kernel145')
backup = out / 'docs-before-closeout-private'
session_name = '145-dsi-deployment-and-session-closeout.md'
assert not backup.exists() and not (root / 'sessions' / session_name).exists()

def read_json(path):
    return json.loads(path.read_text())

def archive(path):
    with tarfile.open(path) as source:
        data = {m.name.removeprefix('./'): source.extractfile(m).read()
                for m in source if m.isfile()}
    for manifest, payload in data.items():
        if Path(manifest).name != 'SHA256SUMS':
            continue
        prefix = str(Path(manifest).parent)
        for line in payload.decode().splitlines():
            digest, name = line.split('  ', 1)
            name = name.removeprefix('./')
            key = name if prefix == '.' else prefix + '/' + name
            assert hashlib.sha256(data[key]).hexdigest() == digest
    return data

runtime = read_json(ref / 'first-runtime-validation.json')
bundle = read_json(ref / 'dsi-observation-build-package-validation.json')
cleanup = read_json(ref / 'cleanup-validation.json')
runtime_data = archive(out / 'first-runtime-private.tar.gz')
closed_data = archive(out / 'inactive-recorder-closeout-private.tar.gz')
closed = json.loads(closed_data['cleanup-validation.json'])
failure = json.loads(closed_data['evidence-private/recorder-failure-validation.json'])
assert runtime['new_boot_verified'] and runtime['kernel_build'] == 145
assert bundle['deployed'] and bundle['actual_runtime_verified']
assert runtime_data['boot-id-private.txt'] == (out / 'embedded-boot-id-private.txt').read_bytes()
assert closed_data['evidence-private/boot-id-private.txt'] == runtime_data['boot-id-private.txt']
assert hashlib.sha256(closed_data['failure-before-cleanup-private.tar.gz']).hexdigest() == closed['failure_archive_sha256']
assert closed['same_verified_runtime_boot'] and closed['boot_link_removed']
assert closed['exact_service_removed'] and closed['own_trace_instance_absent']
assert closed['pidfile_absent'] and closed['gui_three_files_preserved']
assert closed['no_new_counted_faults'] and closed['taint'] == 0
assert not closed['startup_capture_success'] and not failure['failure_cause_confirmed']
assert cleanup['complete'] and cleanup['removed_candidate_files'] == 98
assert cleanup['inactive_build_volumes_compressed_and_verified'] == 5
assert runtime['counts']['dma_tx_prepare_failure'] == 9
assert all(runtime['counts'][key] == 0 for key in ['gpu_faults', 'dpu_timeouts', 'dsi_errors', 'kernel_warns'])

closed['archive_manifest_verified'] = True
closed['archive_sha256'] = hashlib.sha256((out / 'inactive-recorder-closeout-private.tar.gz').read_bytes()).hexdigest()
closed['recorded_startup_results_absent'] = True
closed['recorder_never_started_is_inference_from_absent_outputs'] = True
(ref / 'inactive-recorder-closeout-validation.json').write_text(json.dumps(closed, indent=2) + '\n')
(out / 'inactive-recorder-closeout-validation.json').write_text(json.dumps(closed, indent=2) + '\n')

names = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'HANDOVER-NEXT.md', 'HANDOVER.md',
         'README.md', 'DOCS-INDEX.md', 'linux-port/README.md',
         'linux-port/docs/HARDWARE-STATUS.md', 'linux-port/docs/00-INDEX.md',
         'sessions/145-dsi-observation-and-old-build-cleanup.md']
backup.mkdir(mode=0o700)
for name in names:
    shutil.copyfile(root / name, backup / name.replace('/', '--'))
for name in ['build-validation.json', 'source-validation.json', 'documentation-validation.json']:
    shutil.copyfile(ref / name, backup / name)
shutil.copyfile(out / 'flash-validation.json', backup / 'flash-validation.json')
for name in ['build-validation.json', 'source-validation.json']:
    value = read_json(ref / name)
    value['deployed'] = True
    value['actual_runtime_verified'] = True
    value['startup_trace_captured'] = False
    value['hardware_acceptance_pending'] = True
    (ref / name).write_text(json.dumps(value, indent=2) + '\n')
flash = read_json(out / 'flash-validation.json')
flash['runtime_validation_pending'] = False
flash['actual_runtime_verified'] = True
flash['hardware_acceptance_pending'] = True
(out / 'flash-validation.json').write_text(json.dumps(flash, indent=2) + '\n')

now = dt.datetime.now(dt.timezone.utc)
stamp = now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
summary = ('阶段145已只刷logdump并实际启动，系统/模块仍为132；boot/logdump回读、实际设备树、'
           '770模块、GPT18、persist及NV/原厂来源校验通过。Phosh/Phoc存在、taint0，'
           '累计DPU0/DSI0/GPU0/WARN0/TXprepare9，显示空闲，未做GPU专项负载。'
           '启动追踪未取得结果，未确认启动链根因；失败证据已封存，临时开机服务和自建trace均不再存在。'
           '显示、GPU和充电均未新增验收成功。本轮按用户要求收尾并交接，完整适配目标仍未完成。')
session = f'''# 阶段145：实际部署、启动追踪失败与本轮收尾

{stamp}（Asia/Shanghai）。按用户要求完成进展、文档和交接；本轮结束，不把完整适配目标标为完成。

{summary}

## 已完成与证据边界

145包含144 EUD退出同步修复和新增的DSI原始状态追踪。DSI实际函数24项、EUD实际函数26项宿主测试通过；完整Image/modules/DTB构建、770模块与132逐字节一致、三个initramfs蓝牙模块及FAT只读校验通过。宿主模型不能替代实际时序或硬件验收。

145 Image为59243008字节，SHA256 `{bundle['image_sha256']}`；64MiB logdump SHA256 `{bundle['logdump_sha256']}`。四件套使用boot132、logdump145、modules132、完整rootfs132；实际仅刷logdump，userdata没有全量重刷。独立新boot及运行时保护项已重新取证，不再使用旧140身份作为当前手机身份。

刷写前140停止流程出现70次TX prepare失败，原停止脚本已终态且没有重放。将那一次的完整故障前缀封存后，逐项核实设备已停止、taint0与受保护内容不变，才完成本次切换。该豁免仅绑定旧140/特定日志/特定切换，不能接受145运行错误或用于后续停止流程；70次失败中每一次的通道状态没有记录，不能宣称全部为NULL/DOWN或问题已修。

本次F1回执来自切换前140，主机实际收到后进入启动管理器。145包含144补丁，但145自身退出时的实机回执与panic仍未验证，不能把旧140回执算作该补丁的实机成功。

## 收尾时的实机状态

当前内核构建#145，release仍为`7.3.0-rc6-rmx1931-samurai-k132+`，software generation132。Phosh/Phoc均存在，DRM连接存在但CRTC inactive。taint0，累计DPU timeout0、DSI worker0、GPU fault0、kernel WARNING0、codec ENOSPC0、TX prepare9。最后的临时服务清理前后上述计数一致。空闲、无GPU专项负载和没有新增计数都不能证明显示/GPU稳定，TX prepare9也意味着尚未达到“无报错”。

boot132/logdump145实际分区SHA256、live DTB语义与132、GPT18、persist、NV6/source4/vendor1、784模块树记录（770个模块）和GUI三文件均通过。USB SSH/SCP可用。充电只读驱动仍存在；没有做新的充电控制/温度保护验收。

## 启动追踪失败与临时服务清理

`k145-startup-trace`安装时三文件哈希正确，但新启动没有采集目录、PID文件、输出日志、样本、完成标记或归档，OpenRC状态为stopped。三个DSI追踪事件已在实机注册，当前采集失败不能归结为追踪点缺失。准确的启动链根因尚未确认，本轮不继续重启实验。

使用新的同boot守卫，确认无记录器进程、自建trace、PID文件与结果后，先封存安装源码、OpenRC状态、清理前日志和哈希，再只移除该临时boot链接和完全匹配的init服务。没有杀进程、重放完成-only stop、启动晚采集冒充早期采集或删除诊断源码。失败记录仍保留，GUI三文件不变，清理前后计数无新增。

公开证据在`reference/kernel145/first-runtime-validation.json`、`inactive-recorder-closeout-validation.json`及`dsi-observation-build-package-validation.json`；原始归档、boot ID及日志在私有`E:/edk2-samurai-out/kernel145`。当前身份以该目录`embedded-boot-id-private.txt`和手机`/var/lib/samurai/k145-first-runtime/boot-id-private.txt`为准。主机归档SHA256和内层清单均已核验。

## 下一轮按此顺序继续

1. 先读本记录及`NEXT-SESSION.md`，重新只读核对当前boot、进程与故障计数。收尾归档不能替代下一轮新鲜状态。
2. 检查已封存的OpenRC依赖/启动入口，确认为什么临时服务没有成功采集。先解决启动链、异常封存和清理路径，再建立新前缀、新boot守卫的有界早期采集。旧145安装、停止、冻结、F1、刷写和收尾动作全部终态，禁止重放。
3. 如需再启动，用当前145身份创建新的保护检查与停止流程。不能重用140的70条日志豁免；同步验证145真实F1回执。之后关联DSI原始IRQ/六类寄存器状态/worker复位与DPU kickoff、完成、中断时间线。保持83ms看门狗和原MMIO节奏，不凭调高时钟、延长超时或无负载零计数宣布修复。
4. GPU136两次迟发CCU错误仍未解决。保留`gpu_probe_allowed=false`，先闭合相同VM、提交时刻与BO/CCU关系；不重跑旧33场景或使用全局debug/缓存刷新。
5. 充电138的双电芯目标/恢复阈值8.725V/8.525V证据保持，持续输入、温度、保护、失联和实际控制仍未验收。当前132系统不含134 USB额度驱动；不能由低电流判定控制成功或失败。

## 构建与清理恢复位置

当前源码/Image：WSL `/home/cy122/pmos-samurai-kernel136/kernel`；目录名136不是内核构建版本。新145模块安装树为同级`modules-root145`。私有145镜像、132四件套与140回退镜像均保留；回退前也必须新建当前145守卫，不能重放旧143回退动作。

E盘清理已完成：98个过时产物、8个重复ISO分片移除，5个旧卷完整zstd封存并解压流SHA/长度核验，净释放94.39GiB。该数字属于清理完成时的收据，不代表此刻剩余空间。118/122/126/129/134原卷需要按私有`cleanup145/cleanup-ledger-private.json`还原并验核，不能让旧ensure脚本生成空卷。原C盘WSL、源码、日志、工厂/NV备份不删除，清理动作不得重放。

本轮没有提交、推送、发布或向其他会话发送交接。保留禁止全刷userdata、改NV/GPT/工厂备份、BT配对、振动新增脉冲和FET/OTG/OTP/unseal写入等既有约束。私人身份、地址、密钥、镜像和原始日志不写入公开文档。
'''
(root / 'sessions' / session_name).write_text(session)
next_text = f'''# Realme X2 Pro继续检查点（阶段145收尾，{stamp}）

{summary}

先读[本轮实际部署与收尾](sessions/{session_name})。当前可信证据：reference/kernel145/first-runtime-validation.json、inactive-recorder-closeout-validation.json、dsi-observation-build-package-validation.json；构建与清理历史见145-dsi-observation-and-old-build-cleanup.md。旧“145未部署/手机140”仅代表部署前历史。

当前手机#145/software132，私有身份为E:/edk2-samurai-out/kernel145/embedded-boot-id-private.txt，手机/var/lib/samurai/k145-first-runtime/boot-id-private.txt。WSL /home/cy122/pmos-samurai-kernel136/kernel为源码与Image145，同级modules-root145已安装核验。四件套：boot132/logdump145/modules132/rootfs132；只刷logdump，全部保护检查通过。145真实退出F1/panic仍未验证，现有F1收据来自140。

下一轮先核对当前boot与状态，再分析私有inactive-recorder-closeout归档中的OpenRC启动链。临时boot服务/init服务已移除，旧capture脚本仍在私有手机记录目录；没有可用于分析的145启动trace。修好启动及失败封存流程后，以新前缀/新守卫建立早期有界追踪，关联DSI raw/IRQ/worker边界和DPU帧时序。本轮145及旧143所有现场动作均终态，禁止重放；旧140的70次TX失败封存豁免不能用于145。

GPU136迟发CCU问题仍开放，gpu_probe_allowed=false；先核对相同VM/提交时刻/BO，不重跑旧33矩阵、全局debug或缓存刷新。充电只读证据保持，输入额度、持续输入、温度、保护、失联及控制仍未验收。没有新增硬件通过“安卓般可用”验收。

E盘清理已终态，净释放94.39GiB；5个旧卷已封存。历史E118/122/126/129/134需要按私有cleanup145 ledger完整还原并核验，不能运行旧ensure创建空卷。132/140/145及工厂备份/源码/原始日志保留。

保持83ms看门狗与MMIO节奏，不全刷userdata、不写NV/GPT/工厂备份、不提交推送、BT不配对、振动不新增脉冲、不写FET/OTG/OTP/unseal、不公开私人材料。本轮收尾完成，完整适配目标未完成。
'''
(root / 'NEXT-SESSION.md').write_text(next_text)
(root / 'NEXT-SESSION-PROMPT.md').write_text(f'''# 下一会话短提示词

继续Realme X2 Pro的postmarketOS适配：显示、GPU、充电，目标仍是无报错和日常可用。先读NEXT-SESSION.md及sessions/{session_name}，再读reference/kernel145/first-runtime-validation.json与inactive-recorder-closeout-validation.json。

当前手机#145/software132；四件套boot132/logdump145/modules132/rootfs132，已只刷logdump并实机回读校验。Phosh/Phoc存在、taint0、DPU0/DSI0/GPU0/WARN0/TXprepare9，CRTC inactive，无新专项负载，三个硬件均未新增验收。身份只用私有kernel145/embedded-boot-id-private.txt并重新核对。WSL kernel136目录现为源码/Image145，新modules-root145已核验。

145启动追踪没有采集结果；失败证据已封存，临时开机服务已移除，根因未确认。下一轮先查OpenRC启动链，再用新路径/新boot守卫建立有界早期追踪，并验证145真实退出F1。不要重放旧145/143操作，不要重用旧140的70次TX prepare过渡豁免。GPU136迟发CCU仍开放，gpu_probe_allowed=false；充电控制/温度保护仍待办。

E盘清理已完成并净释放94.39GiB，5旧卷须按私有cleanup145 ledger恢复验证，不运行旧ensure生成空卷。保留83ms看门狗和MMIO节奏、132/140回退与工厂/NV备份。禁止全刷userdata、NV/GPT操作、提交推送、BT配对、振动新增脉冲、FET/OTG/OTP/unseal写入与公开私有材料。上一轮已收尾，完整适配目标未完成。
''')
for name, prefix in [('README.md', ''), ('linux-port/README.md', '../'),
                     ('linux-port/docs/HARDWARE-STATUS.md', '../../')]:
    path = root / name
    text = path.read_text()
    head, rest = text.split('\n', 1)
    old_block = re.compile(r'^\s*最新阶段145：.*?以下为此前历史。\n', re.S)
    rest, changed = old_block.subn('', rest, count=1)
    assert changed == 1
    if name.endswith('HARDWARE-STATUS.md'):
        head = '# RMX1931 Linux 硬件接入清单（2026-10-12，阶段145收尾）'
    path.write_text(head + '\n\n当前阶段145收尾：' + summary +
                    f'\n\n详见[实际部署与收尾]({prefix}sessions/{session_name})。以下为按时间保留的历史记录，旧版本状态不能作为当前操作依据。\n' + rest)
status_path = root / 'linux-port/docs/HARDWARE-STATUS.md'
status = status_path.read_text()
rows = {
    '原生显示面板': '| 原生显示面板 | 当前145/132系统，Phosh/Phoc存在、taint0，DPU0/DSI0但CRTC inactive；DSI三追踪事件已注册，启动trace未采集 | 首次接管、持续绘制、花屏/开关屏/休眠及长稳未验收；优先修复采集启动链 |',
    'GPU': '| GPU | 136固定800×600像素通过后两次迟发CCU翻译fault；当前145未做专项负载，GPU fault0仅为空闲证据 | 相同VM/提交时刻/BO与CCU关系未闭合，gpu_probe_allowed=false；不重跑33场景或全局debug/缓存刷新 |',
    '电池与充电': '| 电池与充电 | 当前145继承132 MP2650持久只读观测；138实际双电芯目标8.725V/恢复8.525V证据保持，当前没有134 USB额度驱动 | 标准输入额度、持续输入/温度/保护/失联及实际控制待验收，不能由低电流推断控制成功或失败 |',
    '普通USB与OTG': '| 普通USB与OTG | 当前145新boot的USB SSH/SCP、boot132/logdump145/GPT/persist回读通过；本次F1来自旧140 | 145内EUD144退出修复的真实F1/panic未验收；OTG/USB3/休眠/冷启动/长稳待办 |',
    '音频': '| 音频 | 当前145累计TX prepare9、无codec ENOSPC/kernel WARN；旧140停止流程70次失败已独立封存，139未提交槽回收保持 | 首次NULL/DMA准备失败与停止生命周期仍未解决；不能将封存过渡故障视为修复，音质/耳机/休眠待办 |'
}
for label, replacement in rows.items():
    status, count = re.subn(r'^\| ' + re.escape(label) + r' \|.*$', replacement, status, count=1, flags=re.M)
    assert count == 1
status_path.write_text(status)

path = root / 'HANDOVER-NEXT.md'
head, rest = path.read_text().split('\n', 1)
rest, count = re.subn(r'^\s*当前以\[NEXT-SESSION\].*?下方为旧历史。\n', '', rest, count=1, flags=re.S)
assert count == 1
path.write_text(head + '\n\n当前交接以[NEXT-SESSION](NEXT-SESSION.md)及[145部署收尾](sessions/' + session_name +
                ')为准：手机145/software132，临时启动服务已清理，硬件未新增验收；本轮结束。下面全部保留为历史，不能重放其操作。\n' + rest)
path = root / 'HANDOVER.md'
text = path.read_text()
title = '# 交接文档：realme X2 Pro (RMX1931 / samurai) EDK2/UEFI 移植'
assert text.count(title) == 1
text = text.replace(title, title + f'\n\n当前状态（{stamp}）以[NEXT-SESSION](NEXT-SESSION.md)和[145部署收尾](sessions/{session_name})为准。' + summary + '\n\n下方2026-10-06正文为历史资料，其“当前Android/卡logo/MU迁移”等不是现在状态，不能作为续作步骤。', 1)
text = re.sub(r'^updated_at: .*$', 'updated_at: "' + now.strftime('%Y-%m-%dT%H:%M:%SZ') + '"', text, count=1, flags=re.M)
body = text.split('---', 2)[-1]
text = re.sub(r'^content_hash: .*$', 'content_hash: "' + hashlib.sha256(body.encode()).hexdigest() + '"', text, count=1, flags=re.M)
path.write_text(text)
for name, prefix, heading in [('DOCS-INDEX.md', '', '当前进展与交接'),
                               ('linux-port/docs/00-INDEX.md', '../../', '当前进展与交接')]:
    path = root / name
    head, rest = path.read_text().split('\n', 1)
    path.write_text(head + f'\n\n{heading}：[阶段145部署与收尾]({prefix}sessions/{session_name})；[下一轮检查点]({prefix}NEXT-SESSION.md)。手机145，显示/GPU/充电未新增验收；下方旧版本描述为历史。\n' + rest)
old_session = root / 'sessions/145-dsi-observation-and-old-build-cleanup.md'
head, rest = old_session.read_text().split('\n', 1)
old_session.write_text(head + f'\n\n本记录是部署前的构建/清理历史。“手机140/145未部署”已被[后续实际部署与收尾]({session_name})替代，清理收据和历史过程仍保留。\n' + rest)

for path in ref.glob('*.py'):
    ast.parse(path.read_text())
report = dict(stage=145, current_phone_kernel=145, current_source_stage=145,
    current_image_stage=145, software_generation=132, deployed=True,
    actual_runtime_verified=True, kernel_build_completed=True,
    inactive_recorder_closed=True, startup_trace_captured=False,
    recorder_failure_cause_confirmed=False, no_new_hardware_accepted=True,
    display_accepted=False, gpu_accepted=False, charging_accepted=False,
    cleanup_completed=True, historical_archived_volumes_require_verified_restore=True,
    latest_documents_updated=True, python_syntax_pass=True,
    current_identity_is_private_kernel145=True,
    previous_actions_terminal_do_not_replay=True,
    session_closed_at_user_request=True, goal_complete=False,
    mirror_sync_pending=True, documentation_checks_pending=True)
(ref / 'documentation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(ref / 'closeout-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K145_CURRENT_PHONE145_DOCS_UPDATED_INACTIVE_RECORDER_CLOSED_HARDWARE_PENDING')
