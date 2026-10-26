from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel191')
# Preserve the exact trial script before correcting its diagnostic-only regex.
trial=ref/'test-online-gps.py';raw=trial.read_bytes();backup=private/'test-online-gps-executed-private.py';assert not backup.exists();backup.write_bytes(raw)
text=raw.decode();lines=text.splitlines();matched=[i for i,line in enumerate(lines) if 'report[option]=' in line];assert len(matched)==1
lines[matched[0]]="  report[option]=[line.strip() for line in text.splitlines() if line.strip().startswith(('card state:','card status:','slot status:'))]"
trial.write_text('\n'.join(lines)+'\n')
(ref/'radio-trial-parser-validation.json').write_text(json.dumps(dict(executed_script_sha256=hashlib.sha256(raw).hexdigest(),corrected_script_sha256=hashlib.sha256(trial.read_bytes()).hexdigest(),diagnostic_parser_only_changed=True,executed_original_saved_privately=True),indent=2)+'\n')
readme=ref/'README.md';text=readme.read_text();marker='## 当前状态、回退与续作'
section='''## DMS电源与UIM补充对照

五分钟测试结束后发现DMS为shutting-down、MM PowerState为OFF；新短会话中GPS Enabled=6时，两次查询仍如此。源码允许failed状态通过SetPowerState(ON)，因此使用标准MM接口开启一次电源，没有请求基带重启；DMS变online、MM PowerState变ON。[活跃GPS电源对照](active-gps-power-validation.json)

Online后再测约90秒，仍无有效GGA/RMC/raw/CNR，结束GPS0并恢复30秒刷新/INFO。不能把原先OFF单独当作无定位的根因，也没有将这个手工开启步骤包装成持久驱动修复。[Online测试](online-gps-validation.json)、[信号分析](online-signal-quality-validation.json)

开启前后，两卡位的Card Status均是no-atr-received，Slot Status均报告absent/active；这是固件接口结果，不替代物理插卡确认。最初只匹配简单引号字符串的解析器漏掉详细/未加引号的状态，后按原始响应字段复核；开启试验的诊断正则也已修正，执行时原脚本私存，没有重做开启操作。[UIM对照](uim-power-comparison-validation.json)

7036.85秒复核仍同boot/taint0，DMS online、PowerState3保持，MM仍failed/sim-missing、无bearer；GPS0/刷新30秒，三个DSP running、所列故障增量0，NV源manifest核对通过。当前保留普通电源ON供后续蜂窝/GNSS排查，不重复开启或重启。补充23文件已字节快照归档，归档/成员哈希通过。[最新状态](radio-final-validation.json)、[补充归档](radio-supplement-export-validation.json)

'''
assert text.count(marker)==1;text=text.replace(marker,section+marker);readme.write_text(text)
path=root/'NEXT-SESSION.md';text=path.read_text();text=text.replace('| 最终5871.48秒 | 同189第二新boot、taint0，三个DSP running、SensorProxy三项Has为1；MM191运行、GPS关闭/刷新30秒、MM报告sim-missing/bearer0。191故障增量0，保留全boot蓝牙重组1 |',
'| 最新7036.85秒 | 同189第二新boot/taint0，MM191、三个DSP保持；DMS online/PowerState3，MM仍sim-missing/bearer0、GPS0/刷新30秒。电源仅开启一次；191故障增量0，保留全boot蓝牙重组1 |')
text=text.replace('[最终](reference/kernel191/final-validation.json)','[最新状态](reference/kernel191/radio-final-validation.json)')
text=text.replace('1. 有效fix/真实接收仍未解决；','1. GPS活跃时DMS仍shutting-down/电源OFF，标准MM开启一次后online/PowerState3，另测90秒仍无fix/CNR；当前保持ON，不重复开启或重启。有效fix/真实接收仍未解决；')
text=text.replace('6. MM的sim-missing未证明用户未插卡，继续卡槽/UIM/注册/数据/通话/SMS。','6. Online前后两卡位no-atr-received，Slot接口absent/active；固件结果不替代物理插卡确认。MM仍sim-missing，继续卡槽/UIM/注册/数据/通话/SMS。')
text=text.replace('191私人归档843c4d47…/42文件、各成员及原新程序哈希通过；','191主归档843c4d47…/42文件、radio补充b6628078…/23文件、各成员及原新程序哈希通过；')
assert len(text.encode())<=6500,len(text.encode());path.write_text(text)
path=root/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();text=text.replace('5871.48秒同189 boot/taint0','7036.85秒同189 boot/taint0，DMS online/PowerState3')
text=text.replace('仍无有效GGA/RMC/raw/CNR，16条SV事件无列表，in-view最多13不算跟踪；','仍无有效GGA/RMC/raw/CNR，16条SV事件无列表；电源OFF改为online后另测90秒仍无fix，in-view最多13不算跟踪；')
text=text.replace('MM仍报告sim-missing，物理卡槽/UIM/真实SIM注册、','DMS已online，但两卡位仍no-atr/slot absent，MM仍sim-missing；物理卡槽/UIM/真实SIM注册、')
path.write_text(text)
print('Radio power/UIM evidence added; current DMS online; NEXT UTF-8 bytes:',len((root/'NEXT-SESSION.md').read_bytes()))
