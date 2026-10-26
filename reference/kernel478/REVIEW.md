# 478：476 执行前离线复核

未发现 476 模板与 461 当前协议之间会阻断执行的差异；无须修改 472 工具或 476 冻结模板。核对包括：configure 后 stepper 才启动、两次 mode2 守卫、BLS-only profile 禁用 AE／DelayedControls／IPE、UID10000 的 capture／stepper／隔离 IPA 实际进程见证、九次控制阶跃与 233 个 SOF、完整卸载与恢复顺序。新鲜 hand-off、精确 363 版本和正式基线仍由本轮 preflight 核验，离线复核不代替它。

461 的配对末字段为 `parameter-buffer-submitted`，它不证明硬件锁存。逐次 `G_CTRL` 已在 472 中执行并检查；日志只打印初始 readback，逐次检查通过由最终 `STEPPER_RESULT result=0` 共同约束。没有单独的逐次 readback 数值日志。BHIST 与物理 SOF 配对，控制元数据不当作外部 stepper 的物理生效证明。

缓存原件收齐后，本地运行：

```text
python3 reference/kernel478/analyse-cached.py --root /private/collected-transaction --output /private/control-delay-review-private.json
```

输入同目录的 `control-capture-private.log`、`state.json`、`control-live-witness-private.json`、`tele-plan-private.json`。该入口先核完整恢复终态及实际运行声明，再调用 SHA 固定的 476 本地分析器；保留曝光／增益升降分别判首变化和平台，无延迟预设。结果含场景数值，应留私有。局部饱和不能仅由均值排除，缺帧／pending／跨下一 SOF／低 SNR 的原规则保留。尚未对本轮新实机原件运行；没有新增光学或遮光要求，也没有 SSH、SDK、上传或 target 执行。
