# 231：GNSS 文件服务与原厂 RFS 布局核查

本阶段只读检查当前 boot230 的 TFTP/RMTFS 日志，并只读挂载本机原厂 vendor/persist 查看 RFS 链接和文件元数据；未读取或改写 NV 内容。16 个快照成员及最终 36 个原生归档成员均已核对，临时挂载已关闭。未重启文件服务、未新增搜星或辅助数据注入。[审计结果](file-service-audit-validation.json)、[健康检查](final-health-validation.json)、[归档](evidence-validation.json)

本机原厂 `mpss/shared` 指向 persist 的共享目录，与固件只读目录是不同命名空间。原厂共享目录也没有 `configs/mcfg_sw/mdtime.txt`。不能把固件 mdtime 简单映射到该共享路径。当前 RRQ 拒绝日志的本地 errno13，并不等于线上 TFTP 错误码2：与运行程序锁定一致的207源码在该 RRQ 分支统一发送错误码1；这是源码推导，没有抓取线上错误包。

固件 mdtime 实际12字节，六次打开不能称六次完整读取：两次 rsize0 只有打开和对端结束，两次 rsize20 发送16字节 DATA（12字节载荷），两次 seek12/rsize8 发送4字节 DATA（空载荷、正常EOF）。没有短读失败证据。`ota_firewall/ruleset` 原厂也不存在；`mcfg.tmp` 曾有两次写打开，运行时仍0字节，不能据此判定内容有效。没有补造规则或借用其他手机配置。

RMTFS 六个 COW 源载入、11条数字回复均为成功，没有本启动文件服务失败证据。这不能还原226的搜星时间线，也没有证明零CNR的根因。解析器已用数字错误回复、格式损坏、空日志、无载荷 DATA 等负对照验证。[解析器](audit-file-services.py)、[负对照](parser-negative-controls-validation.json)

因此没有部署共享路径别名或错误码补丁，没有把这次排查写成 GNSS 修复。TFTP 当前没有原子停止接入和排空机制，客户端可无限等待，安静日志不能证明可以无损热重启。下一项是[232后摄候选](../kernel232/README.md)。用户已要求搁置前摄纯色物体校验，完整外设目标继续。
