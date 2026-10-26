from pathlib import Path
import json

here = Path(__file__).resolve().parent
repo = here.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel226')
labels = ['default', 'high', 'default-aided', 'high-aided']
reports = [json.loads((here / ('loc-r3-' + name + '-validation.json')).read_text()) for name in labels]
debug = json.loads((here / 'receiver-debug-aided-validation.json').read_text())
by_debug = {x['case']: x for x in debug['cases']}
helper = json.loads((here / 'assistance-refresh-validation.json').read_text())
assert helper['status'] == 'refreshed' and helper['validity_before_hours'] == 0 and helper['validity_after_hours'] == 168
assert helper['download_count'] == helper['injection_count'] == 1 and helper['utc_ack_and_completion']
assert len({r['binary_sha256'] for r in reports}) == len({r['decoder_sha256'] for r in reports}) == 1
rows = []
for label, report in zip(labels, reports):
    assert report['program_exit'] == 0 and not report['decode_errors']
    assert report['cleanup']['start_ack'] and report['cleanup']['stop_ack']
    assert report['cleanup']['client_released'] and report['cleanup']['device_closed']
    assert report['engine_states'] == [1, 2] and not any(report['fault_delta'].values())
    assert report['sv']['positive_snr'] == report['sv']['valid_track'] == 0
    states = [x['horizontal_accuracy'] for x in report['commands'] if x['message_id'] == 0x33]
    assert states[1] == (3 if label.startswith('high') else 1)
    masks = sorted(int(v) for v in by_debug[label]['xtra_reported_masks'])
    assert masks == ([31] if 'aided' in label else [0])
    rows.append(dict(case=label,requested_observation_seconds=90,accuracy_readback=states[1],
        xtra_debug_masks=masks,sv_reports=int(report['indication_counts']['37']),
        reports_with_both_lists=report['sv']['ordinary_reports'],
        reports_without_lists=report['sv']['reports_without_either_list'],
        valid_snr_fields_including_dual_format_duplicates=report['sv']['valid_snr'],
        positive_snr_fields=0,valid_track_fields=0,position_status_counts=report['position_status_counts'],
        full_cleanup_verified=True))
final = dict(stage=226,cases=rows,total_requested_observation_seconds=360,
    same_binary_decoder_and_session_start_fields_except_accuracy=True,
    first_pair_used_inherited_aiding_without_fresh_validity_claim=True,
    second_pair_followed_verified_utc_and_xtra_refresh=True,
    current_boot_aiding_validity_hours=168,xtra_debug_mask_changed_from0to31=True,
    positive_cnr_tracking_and_real_fix_still_not_observed=True,
    missing_lists_not_misclassified_as_zero=True,sv_field_counts_include_dual_format_duplicates=True,
    position_status4_is_user_end_not_timeout=True,
    no_rf_lna_voltage_calibration_or_nv_changes=True,no_dms_power_change_flash_or_reboot=True,
    indoor_window_condition_not_eliminated=True,no_claim_of_gnss_fix=True,
    full_peripheral_goal_active=True)
(here / 'final-validation.json').write_text(json.dumps(final,indent=2)+'\n')
table = '\n'.join('| '+r['case']+' | '+str(r['accuracy_readback'])+' | '+str(r['xtra_debug_masks'][0])+' | '+str(r['valid_snr_fields_including_dual_format_duplicates'])+' | 0 / 0 |' for r in rows)
(here / 'README.md').write_text('''# 226：GNSS原始测量与辅助数据四轮对照已完成

2026-10-16。当前仍boot219/Image183、e49/fae1、libcamera r13/config-r8，没有刷写或重启。用户确认无SIM、室内窗边且房间关灯；缺卡状态符合条件，蜂窝业务留待有卡。[基线](baseline-validation.json)、[完整结果](final-validation.json)。GNSS仍没有真实fix/正CNR，不能把本轮诊断写成已适配完成。

同一R3二进制和解析器分别做默认/HIGH×辅助前/辅助后四轮，每轮观察90秒。每次同CID注册、Start、收原始报文、同session Stop、释放CID并close；请求只在HIGH轮多水平精度TLV，其余固定。HIGH确实回读3，但未恢复接收。[原始精度对照](accuracy-ab-validation.json)。

| 条件 | 精度读回 | XTRA调试掩码 | 有效SNR字段（含双格式重复） | 正CNR / TRACK |
| --- | --- | --- | --- | --- |
''' + table + '''

四轮分别89/89/89/90次SV事件；每轮29次同时返回普通/扩展列表，余下60/60/60/61次未提供列表，后者不计有效0。报告的有效SNR均为0、状态均SEARCH；位置status4为USER_END（主动停止），不是TIMEOUT3，也未见PHONE_OFFLINE6或有效fix。固件同时返回两列表，所以累计字段数不代表唯一卫星数。session事件没有返回sessionId，不宣称已核对其匹配。

初两轮没有假定本次启动的辅助数据有效。扩展PQWP7解码表明只有本地almanac；PQWP3的XTRA掩码0、PQWP4星历位0。随后核对并运行现有helper一次：UTC ACK/完成通过，独立固件有效期0→168小时，一次HTTPS下载和标准MM注入。辅助后PQWP3掩码变31、GPS有效XTRA位数30，PQWP7来源从local4转为other-server3。这比“API成功”更进一步证明数据被接收器采用，但仍无正CNR/TRACK。[辅助刷新](assistance-refresh-validation.json)、[前后debug](receiver-debug-aided-validation.json)。XTRA轨道辅助和广播星历有效位分别记录，不由后者0反推注入失败。

GETcriteria在Stop后仍返回最后的HIGH，不代表活动会话；请求intermediate2与GET读回1不一致，分别记账，不把GET当即时活动状态。Start/Stop只有ACK，不等待不存在的成功indication。四轮均观察engine ON→OFF，MM owner/定位属性、watch空闲/0workers、包数据库保持，taint/fault0。[辅助后最终健康](post-aiding-health-validation.json)。

诊断解析已补普通/扩展SV和NMEA、有效位/有限值/严格数组长度。缺失字段保留missing，不当0；扩展NMEA此次仅PQWP7厂商debug，不能说漏了标准定位句并据此解释无fix。合成的expanded-only/invalid/NaN/长度反例与真实四轮均通过。接收器ADC/AGC在变化，不证明天线/RF硬件正常。

预检错误原样保留：首基线误把apk详细说明当版本；R1/R2把0x32服务版本95误标成NMEA掩码且早期standalone枚举假设错误。R3已按固定IDL使用Get NMEA0x3f/掩码63、typed standalone4，服务版本95另列；R2完成采集/清理但包装器因漏扩展NMEA拒绝，不是设备崩溃。离线debug首版不接受空值的失败也私人保留。[更正索引](preflight-corrections-validation.json)、[主来源](loc-layout-source-validation.json)。

首轮私人归档87成员只覆盖辅助前；最终117成员含四轮raw日志、清理状态、辅助payload与最终健康，归档及每成员哈希已核对。坐标、NMEA原文、卫星身份、端点和私人归档指纹不公开。没有保存相机场景、改变照明、写NV、改DMS电源或配对蓝牙。[最终归档](final-evidence-aided-validation.json)。

当前证据不支持把精度字段或缺轨道辅助单独当作零CNR根因。下一步核对RF/LNA/时钟与OEM初始化；室内因素仍未排除，开阔天空/同机Android对照仍有信息价值。191/201已做online负对照、209已做UTC精度负对照，不盲重复。后摄P provider依赖、IMX319、FastRPC初始化发布/退出生命周期、BT phase5与全部外设继续推进，完整goal保持active。[三路源码结论](RESEARCH-FOLLOWUP.md)、[全清单](../../linux-port/docs/HARDWARE-STATUS.md)。
''')
path = repo/'linux-port/docs/HARDWARE-STATUS.md';s=path.read_text();a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段226。前摄r13/config-r8部署保持；GNSS四轮原始测量与辅助对照已完成但仍无fix/正CNR。boot219/e49/fae1保持，全外设goal active。[226报告](../../reference/kernel226/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[b:]
a=s.index('| GNSS定位 |');b=s.index('\n',a)
s=s[:a]+'| GNSS定位 | 226同CID默认/HIGH×辅助前后各90秒，HIGH读回3；现有helper使当前固件有效期0→168h，XTRA debug掩码0→31、GPS有效位30。普通/扩展SV与NMEA均解析，四轮有效SNR仍0/SEARCH，无TRACK，缺列表另计；清理/taint/fault0 | 真实fix/正CNR仍未解决。室内窗边，无无遮挡户外/同机Android基线；不把精度或辅助数据单独当根因。RF/LNA/时钟/OEM初始化、冷启/SSR及完整radio APK/rootfs开放；221星座/黑名单和191/201 online、209 UTC精度负对照保留 |'+s[b:]
a=s.index('| 蜂窝通话与数据 |');b=s.index('\n',a);line=s[a:b]
line=line.replace('当前Power1、failed/原因2、bearer0','用户确认未插SIM，当前Power1、failed/原因2与条件一致')
line=line.replace('不证明物理未插卡','该历史结果不作为插卡故障证据，真实业务待有卡')
s=s[:a]+line+s[b:];path.write_text(s)
(repo/'sessions/226-gnss-raw-reception-and-aiding.md').write_text('''# 226：GNSS原始测量与辅助对照

默认/HIGH×辅助前后四轮各90秒，固件HIGH读回3；现有helper一次UTC/文件注入使有效期0→168h，XTRA debug掩码0→31，仍无正CNR/TRACK/真实fix。诊断支持扩展SV/NMEA且缺失不作0，debug此次仅证明PQWP7扩展路径，不冒称标准定位流已修。

全部原生会话与QMI客户端正常清理，GPS空闲/刷新30，三DSP running、taint/fault0、NV源保持；boot219/e49/fae1/r13保持，未刷写/重启。117成员最终私人归档核对。用户无SIM、室内窗边关灯，后摄、BT、传感器、蜂窝业务和全外设goal继续。[完整报告](../reference/kernel226/README.md)、[检查点](../NEXT-SESSION.md)。
''')
path=repo/'NEXT-SESSION.md';s=path.read_text();intro=s.split('\n\n')[1]
s=s.replace(intro,'2026-10-16，226：GNSS默认/HIGH×辅助前后四轮各90秒结束，HIGH读回3、辅助有效期0→168h且debug掩码0→31，仍无正CNR/TRACK/fix。r13/r8、boot219/e49/fae1保持，全外设goal active。[226记录](reference/kernel226/README.md)、[边界](WORKING-BOUNDARIES.md)、[历史through225](archive/NEXT-SESSION-through225-2026-10-16.md)。',1)
s=s.replace('226辅助后GNSS测试运行中，跟随私人226/capsule原句柄，不重复Start','226四轮及辅助worker均终态，GPS空闲/刷新30')
a=s.index('GNSS226默认/HIGH');b=s.index('\n\n',a)
s=s[:a]+'GNSS226默认/HIGH×辅助前后四轮各90秒：29次/例同时有两SV列表，2932有效SNR字段含双格式重复均0/SEARCH、无TRACK；241次缺列表另记。HIGH读回3。首次独立有效期0，现有helper一次UTC/文件注入→168h，XTRA debug掩码0→31/GPS有效位30，来源local4→server3，但仍无fix。最终117成员归档，初版87成员保留；所有会话Stop/CID释放/设备关闭，taint/fault0。GET停止后仍HIGH不代表活动；intermediate请求2/读回1分别记账。室内窗边，用户无SIM，缺卡符合条件、业务待有卡；不盲重复191/201 online或209 UTC精度负对照。下一步RF/OEM初始化与天空对照；后摄P双芯片依赖、FastRPC完整初始化/发布竞态见226/RESEARCH-FOLLOWUP，未试电/SSR。'+s[b:]
size=len(s.encode());assert size<=6500,size;path.write_text(s)
d=json.loads((private/'current-work-private.json').read_text());d.update(
    state='226 four formal90s cases, current-boot UTC/XTRA restoration, expanded raw/debug decoding and117-member final archive passed; GNSS no-fix remains open; documentation/source/mirror closing',
    active_native_session=None,active_native_context=None,active_build_session=None,transition_pending=False,
    final_native_archive_members=117,current_boot_xtra_validity_hours=168,xtra_debug_mask=31,
    official_gnss_cases=labels,user_confirmed_no_sim=True,next_session_bytes=size,
    next='Finish source/mirror checks, then prioritize RF/OEM initialization evidence and safe offline rear PM8008 dependency/FastRPC initialization candidates; do not rerun accuracy/UTC experiments without new evidence')
(private/'current-work-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(stage=226,formal_cases=4,xtra_validity_hours=168,positive_cnr=0,real_fix=False,next_session_bytes=size,full_goal_active=True)))
