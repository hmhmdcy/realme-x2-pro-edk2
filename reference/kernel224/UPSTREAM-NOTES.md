# 本轮核对的上游设计

- [2026-04-08 CAMSS管线RFC](https://lists.libcamera.org/pipermail/libcamera-devel/2026-April/058088.html)仍使用软件ISP，并把RAW-only的CPU统计、IPA控制及元数据列为待办。本轮0015在固定v0.7.2的CPU路径补齐这一链路；该RFC的硬件ISP目标不能直接当作SM8150已支持。
- [停止时清理请求的上游讨论](https://patchwork.libcamera.org/patch/21537/)要求正确标记取消。本机同一程序依次复现r9重复取消断言、r10未处理RGB输出状态错误；0016以live frame map确定所有权，0017继承捕获状态。修复由相同二进制和断言复验。
- [标准曝光/增益控制语义](https://docs.libcamera.org/master/internal-api/namespacelibcamera_1_1controls.html)区分独立Auto/Manual模式和手动值。当前候选补的是RAW自动统计与结果元数据，标准手动API仍待实现。
