# 227：FastRPC完整发布与模块保活候选

2026-10-16。用户明确手机没有SIM；这解释缺卡状态，GNSS仍按226的零CNR和真实辅助注入结果继续排查。全外设适配目标保持active。

完成FastRPC隔离候选：完整初始化、ready门控、open准入原子化、部分child/双misc失败逆向清理、端点销毁以后才释放devm owner引用、恢复DMA指针。实机只读基线发现FD1/refcount0，补`.owner = THIS_MODULE`并将退出改为初始化逆序。没有对活跃旧驱动热换，没有重启/刷写或电源操作。

最终W=1/modpost、vermagic/符号通过；实际ELF owner重定位及补丁精确应用通过。原函数ASan/UBSan故障注入11例通过，原版负对照检出未初始化kref。51个canonical相关文件及git状态保持；当前部署未改变，SSR/DMA排空和物理传感器尚未验收。

下一步是可回退的受控启动部署验证；后摄P/Q显式device-link设计还须解决gpio-hog与启动前reset保持。详情及公开收据见[227报告](../reference/kernel227/README.md)，历史GNSS对照见[226](../reference/kernel226/README.md)。
