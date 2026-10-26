# 172：WCD耳机检测初始化与扬声器回归

2026-10-14。用户回家要求再测，在171/kernel168上确认两组断续滴声来自手机，左右麦克风/功放关闭对照也通过。随后继续修复耳机软件链：卡级jack单次绑定共享WCD组件，同时保留RX/TX通道图；修正重复set_jack停止检测、失败started标志、micbias复制过早导致0除数及按钮默认单位，并传播初始化错误，补充Mic Jack/AMIC2设备树。[全部证据](../reference/kernel172/README.md)

宿主提取实际函数做ASan/UBSan错误注入通过，旧函数组合复现四项缺陷。W=1音频对象无告警，checkpatch纯对齐换行修复后0，全内核仅原有EUD warning；.config与SD1/显示源保持，770模块兼容132。DTB只变widgets和audio-routing，首次审计属性名错误被拒绝后修核验。UEFI只变DTB模块，BDS171逐字节一致，30条既有模板提示保留。

新171身份正常停止全部DSP/GUI/DRM/功放，prepare0→0；checker上传名称中断后补齐，只续收据尾部。单次F1，USB EIO边界留存，刷boot/logdump172。新boot #172、MBHC偏置2700mV与单次绑定、Headphone/Mic CARD均off，完整分区/NV/桌面通过。初始runtime collector误查不存在的合并CARD控件失败，修成实际两个per-pin控件后同boot通过。

新boot原生四例：左右相关性0.922/0.999、功放开关差18.10/40.01dB；桌面两例0.917/0.926，与同boot原生amp-off区分。分析初次漏参数只重跑分析，未重复播放。最终383.76秒、taint0、关键故障0、PCM/功放关闭、5次启停配平、17控件恢复、NGD suspended；5条capture stop后的WCD underflow继续分析。人工听感确认属于171重放，不移记为172质量验收。

UCM132尚无Headphones/HeadsetMic，耳机软件初始化通过不等于实际插拔/路由出声通过。用户耳机类型问题尚未收到回复，先保留未插入状态。下一步补本机AIF1 RX0/1与AMIC2路由并实测；音乐/人声、首次瞬态、冷启动/休眠、长稳待验，goal active。回退优先完整boot171/logdump171。
