# kernel94：蓝牙模块启动顺序对照（Linux #93）

结果见[sessions/94](../../sessions/94-deferred-bluetooth-and-startup-isolation.md)。本轮恢复DRM/fb0和首次MPSS/Wi-Fi启动，蓝牙加载服务路径错误保留于原镜像；RAM修正版扫描与共存通过，修正版镜像在kernel95继续验证。

构建、CPIO/配置/模块审计、完整分区备份、守卫、受控停机、F1和logdump-only刷写脚本为本机单轮记录。固定boot ID、哈希、路径和输出前缀不可重放；先建立新现场。模块依赖需与vmlinux目标分开，在同一次modpost中构建三个.ko；`M=`表示外置模块，不适用于该准备方式。两次构建失败日志均保留，没有忽略未解析符号。

`samurai-bluetooth`保留本轮已部署原版本的错误路径，以便审计原CPIO。正确路径版本见`../kernel95/samurai-bluetooth`。测试脚本后来增加MGMT索引等待；早期失败输出与成功输出独立保存，不替换失败证据。

只发布自有源码和脱敏摘要。私人固件、镜像、二进制、完整日志、设备身份和凭据位于`E:/edk2-samurai-out/kernel94`。
