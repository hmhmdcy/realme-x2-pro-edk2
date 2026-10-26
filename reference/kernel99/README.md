# 阶段99：AW8697 原生振动

见 [完整记录](../../sessions/99-aw8697-haptics-and-ufs-readiness.md)。Linux #98 已刷boot/logdump，真实EDK2内嵌DTB重建；标准FF、三次短脉冲电气状态及close/SIGKILL/1秒看门狗停振通过，物理振动仍待用户确认。当前5GHz经RAM手动恢复联网，首次自动启动UFS就绪竞态保留；下一阶段持久化修复。

公开仅自有驱动、DTS/patch、FF测试及审计脚本。镜像/固件/工具二进制/原日志/地址/凭据/SSH身份留 `E:/edk2-samurai-out/kernel99`。构建脚本是历史记录，已存在输出和测试目录不可直接重跑。旧DTS工作区镜像保持，实际内核导出是 `sm8150-samurai.dts.after`。

`verify-haptics.py`验证三次短振动；`verify-runtime.py`验证RAM无线恢复、5GHz网络和生命周期；`verify-checkpoint.py`绑定141文件和已刷读回，明确RAM服务与CPIO差异。`prepare-radio-readiness.py`生成有界等待候选，`recover-radio-ram.sh`保存失败目录后恢复，不证明自动启动或冷启动通过。

蓝牙只扫描且当前关闭，不配对连接；NFC无标签只控制器，充电收尾。保留原NV/persist/Android/数据/旧显示快照/rootfs另一线程。全硬件goal仍active。
