# 178：相关机型复查与ADSP重启断链失败

2026-10-14。仍运行kernel176，没有新修改/构建/刷写。复查OnePlus 7T Pro仓库HEAD、实际0039扬声器补丁及WCD/UCM/声学验收方法；与171的Realme原厂SD1/GPIO140证据对照，保留不同功放和麦克风配置的区别。

单次受控ADSP停启实际offline再running，声卡及regmap/MCLK/供电回收后自动恢复、两个旧debugfs句柄EIO、录音可运行；但新声卡恢复后PDR listener超时并再次断链。原窗口有IRQ读-107共26510、config72、mask sync6、ASoC6、PDR timeout1，测试失败，不能写SSR通过。重复错误使kernel ring覆盖旧内容，原日志已单独封存。

失败后原生四例与普通用户桌面左右声学复测通过，最终6172.11秒taint0、PCM关闭、功放85/85配平，NV/persist/部署/模块132保持。主通路当前可用，失败窗口与后来正常窗口分别记录。

待修两个线索：MFD清理children前parent IRQ仍可访问已断链硬件；PDR在list_lock下等待QMI注册回包，server回调也要锁，旧事务结果可能在新UP后发DOWN。后者仍需实际函数并发重现，不当作已证实根因。完整数据、来源与下一步见[178证据](../reference/kernel178/README.md)，完整goal active。
