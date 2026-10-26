# IMX471与CPU ISP补丁

当前libcamera r13/config-r8、CAMSS fae1、IMX471 e49。原helper/1000nm属性/LUT、原生Quad CPU实验/dma_heap、逐配置sensorInfo、捕获快照及RAW统计/停止取消补丁保持；225补独立曝光/增益控制、线程start输出和无效统计目标保持。[完整20补丁锁](../../packages/libcamera/source-lock.json)、[225证据](../../../reference/kernel225/README.md)。

本目录[source-lock](source-lock.json)中的213三补丁源码明确标为历史，当前完整输入在产品配方。候选1024帧控制、安装后256帧控制、72帧16MP元数据、三次40请求生命周期及普通客户端通过。模式元数据取捕获来源，不回显当前请求；光学延迟未标定。

219真实取流和223暗场噪声是像素证据。完整模式TPG普通Bayer不证明真实Quad颜色；CFA/几何/颜色/标定、后置四摄、GPU路径和实时性能仍开放。
