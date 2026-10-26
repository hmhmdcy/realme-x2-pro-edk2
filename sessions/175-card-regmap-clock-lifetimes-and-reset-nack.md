# 175：声卡、regmap与clock生命周期及父设备复位NACK

2026-10-14。kernel175 V4/logdump175已部署，boot/DTB172、UCM173保持。新增card probe/link exit/remove清理、MFD每UP实例的逆序释放、codec-owned interface map/MCLK及初始UP处理。73场景/7负对照、W=1/完整构建和FAT回读通过。

175首启经历两次codec/MBHC绑定但声卡自动可用；codec两个重绑定、父设备一个重绑定通过，4个旧debugfs句柄EIO，mclk随codec删除/重建。第二次父设备绑定出现NGD0x82000000 NACK、MC0x60读-110，后来再探测成功；测试套件未全过。V1等待idle只有3秒的判据错误与V2真实NACK分开保存。

超时恢复后8次录音启停/3次真实暂停、原生四例和普通用户paplay+parecord左右编码检出通过。最终taint0、PCM/功放关闭、37/37配平；上述一次NACK/读/bring-up超时仍开放。实际耳机、音质、冷启动/SSR/休眠/长稳未验。

完整范围与下一步地址/复位和probe失败电源清理见[175证据](../reference/kernel175/README.md)。[174](174-port-interrupt-stop-and-card-reprobe.md)的手工machine恢复与原172 Oops历史保留；不能把175功能回归说成所有可靠性完成。
