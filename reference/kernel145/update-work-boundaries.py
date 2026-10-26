"""Apply the user's removal of temporary project restrictions to the handover."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel145'
out = Path('/mnt/e/edk2-samurai-out/kernel145')
mirror = Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
backup = out / 'constraints-update-private'
assert not backup.exists()
assert not (root / 'WORKING-BOUNDARIES.md').exists()
now = dt.datetime.now(dt.timezone.utc)
stamp = now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
names = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'HANDOVER-NEXT.md', 'HANDOVER.md',
         'README.md', 'DOCS-INDEX.md', 'linux-port/README.md',
         'linux-port/docs/HARDWARE-STATUS.md', 'linux-port/docs/00-INDEX.md',
         'sessions/145-dsi-deployment-and-session-closeout.md',
         'reference/kernel145/documentation-validation.json',
         'reference/kernel145/closeout-validation.json']
for name in ['FLYWHEEL.md', 'EVALUATION-AND-PLAN.md', 'reference/DECISIONS.md']:
    if (root / name).is_file():
        names.append(name)
backup.mkdir(mode=0o700)
for name in names:
    for source_root, subdir in [(root, 'workspace'), (mirror, 'mirror')]:
        source = source_root / name
        if source.is_file():
            saved = backup / subdir / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, saved)

policy = f'''# Realme X2 Pro当前操作边界

{stamp}（Asia/Shanghai）。用户明确要求：“除了仍应保留的边界，其他全部去掉。”本文件是当前项目规则；旧交接、历史会话、脚本注释和测试摘要中的临时禁令及`gpu_probe_allowed=false`不再构成当前操作限制。

只保留以下四类边界：

1. 不误刷、格式化重要分区，不覆盖NV、校准和工厂备份。
2. 不直接操作电池保护FET、OTP或解封，不绕过温控保护、盲目提高充电电压。
3. 刷写或重启前确认当前设备状态；不用旧启动身份执行当前切换，同一次切换状态未明时不盲目重复发送切换命令。
4. 不公开密钥或私人数据；蓝牙保持只扫描、不配对或连接，振动不新增脉冲。

其余项目禁令全部撤销，包括GPU禁测、旧33项测试禁跑、debug/追踪/缓存策略禁改、固定83ms看门狗和寄存器操作时序、充电永久只读、脚本一律禁复用、普通操作反复全量核验，以及提交或推送禁令。可以按适配任务需要测试、修改驱动、复用工具、提交和推送脱敏后的代码与文档。

实验方法、测试规模、日志范围和核验范围由具体工作决定，不要求先证明根因才能复现或测试。正常充电控制和保护链修复可以推进，电池边界仍适用。旧构建卷可以按需要从封存恢复，也可以重新构建；保留的重要备份不得被覆盖。

历史故障、已执行动作、测试失败和未验收功能仍按真实结果记录。撤销限制不代表硬件已经修复，也不把旧收据变成本次操作的证据。历史脚本中的设备身份、分区参数及执行状态应按当前任务使用；这属于上述数据和设备状态边界。
'''
(root / 'WORKING-BOUNDARIES.md').write_text(policy)
current = f'''# Realme X2 Pro继续检查点（阶段145，{stamp}规则更新）

当前操作边界仅以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为准。用户已撤销其余临时限制：GPU测试、整套用例、debug/追踪、时序和缓存策略修改、正常充电控制、工具复用、提交及推送均可按任务需要进行。历史`gpu_probe_allowed=false`不再约束当前工作。

上次收尾时手机#145/software132；boot132/logdump145/modules132/rootfs132，仅刷logdump。Phosh/Phoc存在、taint0，DPU0/DSI0/GPU0/WARN0/TXprepare9，显示空闲。显示、GPU与充电仍未新增验收成功。本次只更新规则，没有新的实机测试结果。

详见[145实际部署与收尾](sessions/145-dsi-deployment-and-session-closeout.md)。实机与清理证据在reference/kernel145/first-runtime-validation.json、inactive-recorder-closeout-validation.json、dsi-observation-build-package-validation.json。它们是当时的记录，其中限制字段不代表当前规则。

当前记录的私有启动身份为E:/edk2-samurai-out/kernel145/embedded-boot-id-private.txt及手机/var/lib/samurai/k145-first-runtime/boot-id-private.txt。执行下一次刷写或重启时确认实际状态。源码和Image在WSL /home/cy122/pmos-samurai-kernel136/kernel，目录名136不是当前构建版本；modules-root145已核验。145真实退出F1/panic尚未验证，既有F1收据来自140。

后续可以修复启动追踪链、分析DSI/DPU时序，或通过GPU负载及映射追踪定位136迟发CCU问题；正常充电控制、输入额度、温度与保护链也是待办。无需等待同一VM/BO关系或完整根因先闭合才开始测试。145早期启动trace未取得，临时服务已移除；原系统display/radio实例的数据仍可按实际覆盖范围使用。

E盘已净释放94.39GiB，5个旧卷封存于私有cleanup145目录；可恢复或为后续工作重新构建。132/140/145产物、工厂备份、源码和原始日志目前仍保留。

仅保留：重要分区/NV/校准/工厂备份不误写；电池FET/OTP/解封及温控、电压边界；刷写/重启使用当前设备状态，不盲目重复切换；不公开密钥和私人数据，蓝牙不配对/连接，振动不新增脉冲。完整适配目标未完成。
'''
(root / 'NEXT-SESSION.md').write_text(current)
(root / 'NEXT-SESSION-PROMPT.md').write_text('''# 下一会话短提示词

继续Realme X2 Pro的postmarketOS适配：显示、GPU、充电，目标为无报错和日常可用。当前规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)，用户已明确撤销除此文件四类边界之外的全部临时限制。GPU/整套测试、debug/追踪、时序及缓存策略修改、正常充电控制、工具复用、提交推送均可推进；旧gpu_probe_allowed=false不再适用。

进展见[NEXT-SESSION](NEXT-SESSION.md)及[145部署收尾](sessions/145-dsi-deployment-and-session-closeout.md)。上次手机#145/software132，DPU0/DSI0/GPU0/WARN0/TXprepare9、taint0、Phosh/Phoc存在、CRTC inactive；三项硬件均未新增验收。源码/Image位于WSL kernel136目录，实际版本145。145早期追踪失败已封存、临时服务已移除；GPU迟发CCU和充电控制/保护仍待解决，可按定位需要测试，不要求先闭合根因。

仅保留重要分区/NV/校准/工厂备份、电池FET/OTP/解封及温控电压、当前设备身份与切换状态、密钥和私人数据保护；蓝牙不配对或连接，振动不新增脉冲。刷写或重启前确认当前状态。其余限制已撤销。
''')

for name, prefix in [('HANDOVER-NEXT.md', ''), ('README.md', ''), ('DOCS-INDEX.md', ''),
                     ('linux-port/README.md', '../'), ('linux-port/docs/HARDWARE-STATUS.md', '../../'),
                     ('linux-port/docs/00-INDEX.md', '../../'), ('FLYWHEEL.md', ''),
                     ('EVALUATION-AND-PLAN.md', ''), ('reference/DECISIONS.md', '../')]:
    path = root / name
    if not path.is_file():
        continue
    text = path.read_text().replace('下面全部保留为历史，不能重放其操作。',
                                    '下面保留为历史，操作边界采用最新用户规则。')
    head, rest = text.split('\n', 1)
    path.write_text(head + f'\n\n当前操作规则：[WORKING-BOUNDARIES]({prefix}WORKING-BOUNDARIES.md)。用户已撤销其余临时禁令；下方历史中的GPU禁测、固定时序、只读、禁复用及禁提交推送等条款不再适用。硬件状态和既有失败记录仍保留。\n' + rest)

path = root / 'HANDOVER.md'
text = path.read_text()
title = '# 交接文档：realme X2 Pro (RMX1931 / samurai) EDK2/UEFI 移植'
assert text.count(title) == 1
text = text.replace(title, title + '\n\n当前操作规则仅以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为准；用户已撤销其他临时禁令，历史限制不再适用。', 1)
text = re.sub(r'^updated_at: .*$', 'updated_at: "' + now.strftime('%Y-%m-%dT%H:%M:%SZ') + '"', text, count=1, flags=re.M)
body = text.split('---', 2)[-1]
text = re.sub(r'^content_hash: .*$', 'content_hash: "' + hashlib.sha256(body.encode()).hexdigest() + '"', text, count=1, flags=re.M)
path.write_text(text)

path = root / 'linux-port/docs/HARDWARE-STATUS.md'
text = path.read_text()
text, count = re.subn(r'^\| GPU \|.*$',
    '| GPU | 136固定800×600像素通过后两次迟发CCU翻译fault；上次145未做专项负载，根因未解决 | GPU禁测已撤销，可用负载、映射诊断、完整用例及驱动修改继续定位；是否修复以实际结果记录 |',
    text, count=1, flags=re.M)
assert count == 1
text, count = re.subn(r'^\| 电池与充电 \|.*$',
    '| 电池与充电 | 145继承132 MP2650只读观测；138目标/恢复阈值证据保留，控制及保护尚未验收 | 永久只读限制已撤销，可推进正常充电控制、输入额度与保护链修复，保留电池安全边界 |',
    text, count=1, flags=re.M)
assert count == 1
path.write_text(text)

path = root / 'sessions/145-dsi-deployment-and-session-closeout.md'
text = path.read_text()
head, rest = text.split('\n', 1)
text = head + '\n\n后续用户已撤销临时限制，当前仅保留[WORKING-BOUNDARIES](../WORKING-BOUNDARIES.md)中的四类边界。本记录的历史操作和测试结果保留，下一轮规则已同步更新。\n' + rest
start = text.index('## 下一轮按此顺序继续')
end = text.index('## 构建与清理恢复位置', start)
text = text[:start] + '''## 后续可继续的工作

可以修复OpenRC启动追踪链并分析DSI/DPU时序，也可以通过GPU负载、映射事件和驱动候选继续定位迟发CCU故障，或推进充电控制与保护链。工作次序按实际线索选择，GPU测试、整套用例、debug、缓存与时序修改不再受原临时禁令限制。

旧脚本、采集器和工具可以复用或修改。刷写、重启和切换仍按当前设备状态执行，既有旧140停止故障和F1收据只证明当时的结果。普通读取和宿主分析不要求重复全量核验所有模块、NV和分区。

''' + text[end:]
text = text.replace('；回退前也必须新建当前145守卫，不能重放旧143回退动作。',
                    '；需要回退时确认当前设备及分区状态。')
text = text.replace('118/122/126/129/134原卷需要按私有`cleanup145/cleanup-ledger-private.json`还原并验核，不能让旧ensure脚本生成空卷。原C盘WSL、源码、日志、工厂/NV备份不删除，清理动作不得重放。',
                    '118/122/126/129/134旧卷可按私有`cleanup145/cleanup-ledger-private.json`从封存恢复，也可为新工作重新构建。原C盘WSL、源码、日志和工厂/NV备份目前仍保留；重要备份不覆盖。')
text = text.replace('保留禁止全刷userdata、改NV/GPT/工厂备份、BT配对、振动新增脉冲和FET/OTG/OTP/unseal写入等既有约束。',
                    '当前操作规则已由后续用户指示改为仅保留WORKING-BOUNDARIES.md的四类边界，其他临时禁令撤销。')
path.write_text(text)

policy_data = dict(policy_scope='Realme X2 Pro postmarketOS project',
    effective_user_instruction='除了仍应保留的边界，其他全部去掉',
    effective_at=now.isoformat(), canonical_document='WORKING-BOUNDARIES.md',
    retained_boundaries=['important_partition_nv_calibration_factory_backup',
        'battery_protection_fet_otp_unseal_temperature_voltage',
        'current_device_state_before_flash_or_reboot_no_blind_switch_repeat',
        'private_data_keys_bluetooth_scan_only_no_new_haptic_pulses'],
    all_other_temporary_project_restrictions_removed=True,
    gpu_probe_allowed=True, complete_test_suites_allowed=True,
    debug_and_tracing_allowed=True, watchdog_and_mmio_changes_allowed=True,
    cache_strategy_changes_allowed=True, normal_charging_control_allowed=True,
    tools_and_scripts_reusable=True, full_integrity_checks_not_required_for_every_operation=True,
    commits_and_sanitized_pushes_allowed=True,
    historical_gpu_probe_flags_are_not_current_policy=True,
    hardware_acceptance_unchanged=True, phone_operated_for_this_policy_update=False,
    goal_complete=False)
(ref / 'current-work-policy.json').write_text(json.dumps(policy_data, ensure_ascii=False, indent=2) + '\n')
for name in ['documentation-validation.json', 'closeout-validation.json']:
    path = ref / name
    data = json.loads(path.read_text())
    data.pop('previous_actions_terminal_do_not_replay', None)
    data.pop('historical_archived_volumes_require_verified_restore', None)
    data.update(previous_actions_completed=True, archived_build_volumes_recoverable=True,
                current_policy_document='WORKING-BOUNDARIES.md',
                all_other_temporary_project_restrictions_removed=True,
                gpu_probe_allowed=True, normal_charging_control_allowed=True,
                policy_updated_after_closeout=True)
    path.write_text(json.dumps(data, indent=2) + '\n')

for name in ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md']:
    text = (root / name).read_text()
    for forbidden in ['gpu_probe_allowed=false；先', '保留83ms', '保持83ms', '不重跑旧33',
                      '不提交推送', '禁止重放', '不运行旧ensure', '先闭合相同VM']:
        assert forbidden not in text, (name, forbidden)
for name in ['WORKING-BOUNDARIES.md', 'NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md']:
    for target in re.findall(r'\]\(([^)]+)\)', (root / name).read_text()):
        if '://' not in target and not target.startswith('#'):
            assert ((root / name).parent / target.split('#')[0]).is_file(), target
names += ['WORKING-BOUNDARIES.md', 'reference/kernel145/current-work-policy.json',
          'reference/kernel145/update-work-boundaries.py']
for name in names:
    dest = mirror / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, dest)
    assert (root / name).read_bytes() == dest.read_bytes()
health = subprocess.run(['bash', str(root / 'linux-port/scripts/docs-health-check.sh')],
                        capture_output=True, timeout=60)
backup.joinpath('documentation-health-private.txt').write_bytes(health.stdout + health.stderr)
assert health.returncode == 0 and b'RESULT: clean' in health.stdout
report = dict(user_requested_policy_update_applied=True,
    only_four_retained_boundaries=True, other_temporary_project_restrictions_removed=True,
    gpu_probe_allowed=True, normal_charging_control_allowed=True,
    commits_and_sanitized_pushes_allowed=True, active_handover_and_status_updated=True,
    historical_hardware_results_preserved=True, current_policy_overrides_old_snapshot_flags=True,
    updated_files=len(names), local_mirror_byte_identical=True,
    new_document_links_verified=True, documentation_health_clean=True,
    phone_operated=False, committed=False, pushed=False, goal_complete=False)
backup.joinpath('policy-update-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
