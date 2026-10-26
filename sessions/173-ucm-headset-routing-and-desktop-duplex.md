# 173：耳机UCM路由与桌面双向音频

2026-10-14。保持kernel/boot/logdump/DTB172，新增四设备UCM和事务式路由助手。本机AIF1 RX0/1→INT1/2耳机、AMIC2/ADC2→DEC1/TX1耳麦；真实jack掌管端点，助手预置FE后端、单播放BE/单TX、串行及出错恢复、重复路由不重启流。用户明确“暂时没有耳机”，未模拟CARD插入。[详细记录](../reference/kernel173/README.md)

8个宿主路由场景/63处提交后错误注入通过；临时UCM普通用户三种组合、inactive、寄存器读回及恢复通过。首次Mic Jack Switch采集假设错误，-b -未执行命令和错误文本检查均被守卫揭出并修正。V1发现模块重载遗漏alsa-card子模块造成重复，恢复旧文件后清除三个残留模块，才恢复唯一声卡；V2工具补上子模块清理后部署通过。显式冲突列表移除后Pulse仍生成四组合profile，未宣称只有一个profile。

最终四设备CARD已出现，当前HiFi (Mic, Speaker)，耳机/耳麦not available，音量、模拟增益、Class-H和jack端点保持。全零Headphones播放+Headset捕获同时RUNNING、144000单声道帧通过，仅为数字PCM证据。四个原生左右编码音/功放关闭对照检出0.921/0.999、20.00/41.22dB。用户paplay+parecord两路桌面闭环检出0.901/0.936、18.66/40.17dB，source/sink volume/mute保持，所有录音私人保存。

原现场缺端口切换策略模块，系统启动文件已有命令，现场补载。最终同boot4583.58秒、taint0/关键故障0、单CARD与策略存在、PCM/功放关闭、22启停配平、17原控件恢复、NGD suspended、模块132/NV通过；8条capture stop后的WCD underflow仍待定位。内核源码/Image/DTB172保持，rootfs安装器三个文件及POSIX权限实测通过。

未验收：实际插拔/自动profile选择/耳机声道/耳麦/按钮、正常音质、首次瞬态、重启策略加载、冷启动/休眠与长稳。用户无耳机不重复询问，继续独立软件工作，goal active。内核回退优先boot171/logdump171，软件UCM132原件及全部失败收据保留。
