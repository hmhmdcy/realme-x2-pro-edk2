# 378：配置别名移出 debug 映射；实机 CONFIG_IO 首次确认

在原有 shared IOVA 保留范围内把配置槽从 `0x07420000` 移到 `0x07600000`，避开固件的 1 MiB debug 映射，并增加有界的 HFI header/payload 诊断。未扩大 DMA mask、添加 DT 保留区或改动板级资源。

实机 INIT/PING/RT create、MAP 与 CONFIG_IO 均收到确认，scratch 返回 48 字节。UNMAP 回复头为成功，但驱动把未定义的尾部旧值解释为错误；随后重试 UNMAP 得到拒绝，走强制复位清理并自动重启。正常 PC 流程未到达，旧 worker 仍是 terminal=false；见 [本次窗口审计](attempt-audit-validation.json)。不将该实验记为完整配置链路通过。

对原厂 `CreateCallbackData`、MAP/UNMAP 分支与 `ReleaseCallbackData` 的进一步执行确认：44 字节 MAP/UNMAP ACK 的头已初始化，12 字节尾部保留分配器内容，不能按 CONFIG_IO/DESTROY 的 payload 状态解释。377 的零填充分配器模型掩盖了这个区别。[379](../kernel379/README.md) 增加非零填充分配器和旧解析器反例后修正并实机通过。

已在新启动核对原 boot366/logdump365、taint0、CPU0-7、17 个 ICP/BPS/IPE 时钟关闭且临时模块/DT 无残留；按哈希移除临时固件，原固件和失败事务保留。当前 guard 为 `/var/lib/samurai/k378-recovered/boot-id-private.txt`。379 在此同一启动完成两路配置和四摄回归，原始日志仅私存。
