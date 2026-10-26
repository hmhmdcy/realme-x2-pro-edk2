# 169：同一kernel168第二次启动与停止回归

2026-10-14。按168首次boot的新身份正常停止桌面、无线与ADSP，所有remoteproc离线、无DRM用户态client、CRTC关闭、双功放关闭静音，taint0。全停止过程中DMA prepare从0保持0；旧163在同流程新增70次。[停止验证](shutdown-validation.json)

F2FS冻结、单次F1和当前bootloader核对后，仅fastboot reboot，未新增刷写。第二次boot身份与首次不同，仍kernel168、WCD版本0x411、桌面存在，所有音频初始化关键计数0、taint0。[第二次启动](runtime-validation.json)

第二boot再做3次2秒原生播放、3路各3秒DMIC采样和桌面播放，均返回0；mixer恢复、功放关闭静音，无新增DMA/TX/queue/resume/WARN，taint0。三路均144000帧，去掉首0.5秒后非零、满幅削波0。[第二次音频](audio-validation.json)

本轮启动属于经F1/fastboot的重启，未验证断电冷启动。采样统计不证明实际拾音质量，实际听音及耳机操作按用户本轮回复暂缓。

第二boot再做121.43秒/21次空闲采样：同boot/桌面PID、taint0、关键计数0、PCM关闭、功放关闭，NGD最终runtime suspended。[空闲观察](idle-validation.json)

最终当前boot的boot164/logdump168真实读回、persist/NV及现用770模块核对保持；主Image与三个音频源文件和构建168哈希匹配，tracked差异仅三个音频文件。[最终现场](final-validation.json)、[当前组合](current-validation.json)
