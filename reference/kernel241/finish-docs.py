from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel241')
p=ROOT/'NEXT-SESSION.md';text=p.read_text()
(P/'checkpoint-before-size-repair-private.md').write_text(text)
start=text.index('## 241 GNSS专项续作');end=text.index('## 最后已验证部署',start)
text=text[:start]+text[end:]
old='2026-10-16文档及约束清理。适配目标 **paused（已暂停、未完成）**；240结论为progress。后续继续/修复/测试请求即可推进，无需重复确认。本轮未连接或复测手机。设备状态来自[240最后健康记录](reference/kernel240/final-health-validation.json)，接手时核对实际状态。'
new='2026-10-16 241已继续GNSS专项：630秒对照后仍无正CNR/fix，根因未定，见[241分析](reference/kernel241/README.md)。四探针已Stop/release/close，定位空闲、三DSP运行、taint0/本轮fault增量0；未改生产服务、刷写或重启。[当前专项健康](reference/kernel241/final-health-validation.json)。其它功能沿用240核对与待办。'
assert text.count(old)==1;text=text.replace(old,new)
old='GNSS正CNR/fix未解决。实际ODM gps.conf与社区固定源相同，但HAL库固定vendor路径、无ODM fallback；ZIP安装声明不证明运行采用。建议对照匹配Android运行映射/初始化日志与Linux QMI差异；RF_LOSS报告逻辑不证LNA配置，已有同CID/GSV/辅助矩阵可作复测对照。手机室内窗边、无SIM；蜂窝真实注册/通话/数据待有卡条件。蓝牙/传感器长稳及全机kernel/rootfs继续开放。'
new='GNSS见[241逐项对照](reference/kernel241/README.md)：实际HAL保留LPP/LPPe分支；AFW、master及Start前测量配置未恢复接收，0xD0被error57拒绝；534/540测量事件均缺SV数组，不计0。SUPL读回2.0，其余查询缺字段不猜值。仍室内窗边/无SIM，待同机Android或无遮挡天空对照。其它外设/全机整合待办保持。'
assert text.count(old)==1;text=text.replace(old,new)
p.write_text(text)
print('NEXT-SESSION bytes',p.stat().st_size)
lock={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.is_file() and p.name!='source-lock.json'}
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
