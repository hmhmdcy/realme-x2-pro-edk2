"""Record the scoped GNSS continuation without overwriting camera history."""
from pathlib import Path
import ast,hashlib,json
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
health=json.loads((R/'final-health-validation.json').read_text())
assert health['all_probe_processes_exited'] and health['location_enabled']==0 and health['taint']==0
for name in ['differential','ordered','afw','combined']:
    report=json.loads((R/(name+'-validation.json')).read_text())
    assert report['program_exit']==0 and report['cleanup']['client_released'] and report['cleanup']['device_closed']
    assert json.loads((R/(name+'-export-validation.json')).read_text())['all_members_verified']
for p in R.glob('*.py'):ast.parse(p.read_text())

nextfile=ROOT/'NEXT-SESSION.md';text=nextfile.read_text()
marker='## 最后已验证部署'
insert='''## 241 GNSS专项续作

2026-10-16用户继续GNSS初始化对照；本专项已实测，零CNR根因仍未确定，其余全外设事项沿用240交接。详见[241调用链与结果](reference/kernel241/README.md)。当前仍236启动、MM程序/包库未改，四个诊断worker均终态，定位Enabled0/Signalsfalse/rate30、辅助空闲，三DSP运行、taint0、本轮故障增量0；本轮未重新核全量模块或相机功能。

实际vendor库保留LPP/LPPe调用，与公开AOSP注释版本不同；事件注册显式AFW=1，Linux省略；master0xBA及测量配置0x88成功，平台RESUME0xD0被固件ACK error57拒绝。630秒对照含AFW单变量/组合，正CNR/TRACK/fix均未出现；master运行中加入后的缺数组不当0，Start前顺序及组合的534/540条测量事件也全部缺SV数组。SUPL读回2.0，LPP/LPPe未返回；没有重注入XTRA或更新生产服务。下一项有区分力的证据是同机匹配Android实际初始化/接收对照或无遮挡天空复测，不将室内负结果推为LNA损坏。

'''
assert text.count(marker)==1 and '## 241 GNSS专项续作' not in text
nextfile.write_text(text.replace(marker,insert+marker))

status=ROOT/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text()
text=text.replace('用途：当前硬件验收清单。','用途：当前硬件验收清单。241于2026-10-16专项复测GNSS，其余功能核对仍按240；[241初始化与接收对照](../../reference/kernel241/README.md)。',1)
lines=text.splitlines()
for index,line in enumerate(lines):
    if line.startswith('| GNSS定位 |'):
        lines[index]='| GNSS定位 | 241实际vendor调用链/CFI跳板/虚表与当前MM源码核对；AFW注册字段、master0xBA、测量0x88及顺序对照630秒。Start前master/AFW各890、组合916有效SNR字段全0/SEARCH；534/540测量事件均缺SV数组。0xD0被ACK error57拒绝；SUPL2.0读回，LPP/LPPe未返回。四worker Stop/release/close通过，定位空闲、taint0/本轮fault增量0；226辅助前后矩阵独立保留 | 正CNR/TRACK/真实fix仍未解决。master运行中阶段缺列表不计0；本轮未重注入XTRA或证明当前有效期。实际库LPP/LPPe分支不能套用公开AOSP注释结论，字段差异不当根因。用户仍室内窗边/无SIM，无同机Android/无遮挡天空基线；不猜LNA接线、不以更多NMEA事件作为接收修复 |'
status.write_text('\n'.join(lines)+'\n')

indexfile=ROOT/'DOCS-INDEX.md';text=indexfile.read_text();old='| GNSS标准链路、相关机型与modem文件服务 | '
assert text.count(old)==1
indexfile.write_text(text.replace(old,old+'[241本机HAL调用对照与630秒实测](reference/kernel241/README.md)、'))

lock={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.is_file() and p.name!='source-lock.json'}
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print(json.dumps(dict(stage=241,scoped_gnss_checkpoint_recorded=True,source_files=len(lock),all_native_contexts_terminal=True,root_cause_proven=False)))
