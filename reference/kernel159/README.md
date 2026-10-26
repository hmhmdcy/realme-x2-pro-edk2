# 159：同一 #158 镜像的第二次启动验收

不新增构建或刷写。先核对当前158启动身份，保护分区/NV/模块哈希，完成全套停机及F2FS冻结，一次F1受理并正常进入bootloader；重新核对设备/产品后仅执行fastboot reboot。未使用紧急SysRq。

新boot的实际内核仍为#158，CTRL=0x1f5先停至0，再完成CTL0清理及native DSI初始化。Phosh uptime19.56秒，158首次为19.99秒，155旧流程79.67秒。全boot KMS初始化失败、DSI错误、DPU timeout、GPU fault、WARN均0，taint0；此次audio DMA prepare0，不能由此宣称音频问题已修复。[运行核验](runtime-validation.json)、[启动时间](boot-timing-validation.json)

启动记录器17.72秒就绪、93.05秒无丢失，早期bootconfig trace也无丢失。实际初始TX wait发生在PP TX done之后约44微秒，ret=0。24次标准DPMS和12次背光门控顺序再次通过，两次158启动累计48次电源转换。[启动顺序](first-startup-order-validation.json)、[电源回归](cycles-validation.json)

临时159启动服务已停止并从boot runlevel删除。连续601.09秒、21次采样直到uptime1006.20秒，同一boot和桌面PID保持，关键错误与UFS UIC timeout均0，taint0；没有重现未经指令的重启。[稳态结果](steady-validation.json)

实体“命令行→锁屏”白屏/花屏过渡反馈待补。用户已确认158手动开关屏无闪屏，并确认157异常重启期间没有人为操作；157的重启原因仍未知，保留原始现场。[当前验收范围](current-validation.json)

完整启动与回归私人档案SHA256：`799af549ab2cdd0fc754e73e1b07b0a6321056e2edaae9222d6c65839629f2dd`。原始日志不放入公开文档。工具旧输出标签曾写SAME154，实际镜像/guard/内核均158，标签已修正且未重发重启。
