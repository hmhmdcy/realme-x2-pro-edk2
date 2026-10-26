from pathlib import Path
import json

here = Path(__file__).resolve().parent
repo = here.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel226')
assert json.loads((here / 'assistance-refresh-validation.json').read_text())['status'] == 'refreshed'
path = repo / 'NEXT-SESSION.md'
s = path.read_text()
old = s.split('\n\n')[1]
new = '2026-10-16，226进行中：前摄r13/r8部署保持；GNSS原始QMI默认/HIGH各90秒均无正CNR/TRACK，HIGH读回3。当前辅助数据独立查询0→168小时已刷新，辅助后复测中。全外设goal active。[226记录](reference/kernel226/README.md)、[边界](WORKING-BOUNDARIES.md)、[历史through225](archive/NEXT-SESSION-through225-2026-10-16.md)。'
s = s.replace(old, new, 1)
s = s.replace('运输reference/kernel225/host.py', '运输reference/kernel226/host.py')
s = s.replace('guard /var/lib/samurai/k225-baseline/boot-id-private.txt', 'guard /var/lib/samurai/k226-baseline/boot-id-private.txt')
s = s.replace('与219-runtime/220至224-baseline同boot', '与219-runtime/220至225-baseline同boot')
s = s.replace('225事务verified，构建/原生测试均终态', '225事务verified；226辅助后GNSS测试运行中，跟随私人226/capsule原句柄，不重复Start')
a = s.index('GNSS无fix/正CNR、室内窗边；');b = s.index('\n\n', a)
s = s[:a] + 'GNSS226默认/HIGH各90秒：每例89次SV报告，29次同时有普通/扩展列表，748有效SNR字段（含双格式重复）均0/SEARCH、无TRACK；60次缺列表不计0。HIGH读回3仍无改善。完整解析扩展PQWP7后见XTRA掩码0、星历位0、仅本地almanac；现有helper一次UTC/一文件注入，独立有效期0→168h，辅助后复测正在运行，未动DMS电源。房间关灯/室内窗边，用户确认无SIM；缺卡符合条件，业务待有卡。226首轮87成员归档仅覆盖辅助前，后续记录尚待追加归档。相关机型/191与201 online负对照、209 UTC精度负对照保留，不盲重复。207MCFG/RAM复制等历史见through225。' + s[b:]
size = len(s.encode())
assert size <= 6500, size
path.write_text(s)
d = json.loads((private / 'current-work-private.json').read_text())
d.update(active_native_session=10986,active_native_context='/var/lib/samurai/k226-loc-r3-default-aided',
    state='Fresh verified helper restored current-boot validity0to168h; aided default90s confirmed live',
    next='Follow aided capture to terminal; if still no reception compare aided HIGH, then inspect updated RF/aiding telemetry; preserve full peripheral scope',
    preliminary_native_archive_members=87,preliminary_archive_covers_only_pre_aiding=True,
    research_followup='reference/kernel226/RESEARCH-FOLLOWUP.md',next_session_bytes=size)
(private / 'current-work-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(stage=226,progress_checkpoint_saved=True,next_session_bytes=size,full_goal_active=True)))
