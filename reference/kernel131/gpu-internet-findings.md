# GPU专项检索（2026-10-12）

已实际搜索`freedreno CCU TRANSLATION fault`、`a640 gpu fault freedreno`、`CCU SMMU_TABLE_UPDATE fault`及缓存/页表相关关键词，并阅读以下一手来源。未找到已经证明可直接解决本机故障的补丁，检索结果不是适配验收。

1. [POCO X3 Pro postmarketOS适配作者的实机记录](https://github.com/alexandr-mironov/poco-x3-pro-postmarketos/blob/main/README.md)：同为Adreno640/SM8150，Mesa26.1.6及kernel7.0，记录相同`dir=READ type=TRANSLATION source=CCU`与后续ring故障、GPU reset。其Phoc空纹理检查仅防止合成器崩溃，记录仍有画面错误，不能作为GPU根因修复或直接套用于本机。两台设备/触发场景/版本不同，尚未证明同一根因。
2. [Mesa官方Freedreno文档](https://docs.mesa3d.org/drivers/freedreno.html)：CCU用于渲染目标/resolve相关访问，解释devcoredump与crashdec估计停点受流水线影响；本机已按该流程保存并解码。同步/缓存/陈旧内存是排查类别，不能直接判定为本机原因。
3. [Linux官方a6xx驱动](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/msm/adreno/a6xx_gpu.c)：已核对当前本地129源码确实包含CCU depth/color失效事件及SMMU页表更新。旧的“补缺失CCU invalidate”描述不能仅凭关键词再套补丁。本机新dump估计在页表更新附近，仍需与完整提交/映射生命周期交叉证明。

本轮不添加全局flush绕过、不删除fault日志、不部署仅让Phoc存活的替代修复。尺寸问题已实测定位为测试工具缺陷；CCU迟发故障独立开放。用户要求长期难错先留档换项，下一项为标准充电观测持久接入；后续GPU调查依据新转储核对缓存与映射生命周期，并保留有界实机验证要求。
