# 传感器测试图案与真实CFA的边界

219补做两组各六帧RAW10测试图案统计。仅计算每条色带中间一半区域的4×4采样相位均值，排除边界混合；原始像素仍只在DMA同步区间驻留内存，没有保存图片。[探针构建](pattern-layout-build-validation.json)、[4MP结果](pattern-layout-2304x1728-validation.json)、[16MP结果](pattern-layout-4608x3456-validation.json)。

两种模式生成的图案均每2×2重复。按单像素CFA分组，组内最大均值差为0；按2×2同色单元分组，即使遍历四种起点偏移，最大差仍为1023。这说明当前完整模式的内部TPG并未模拟真实Quad Bayer滤色阵列的同色单元。4MP生成的通道签名也与完整模式不同，不能直接拿它反推真实滤色阵列顺序。

因此，此前完整RGB测试图案通过的含义是：真实传感器完整尺寸输出可经CAMSS、缓冲分配与CPU路径产生六帧非零RGB。它没有证明这些色条经过Quad算法后颜色正确。218的独立合成Quad输入逐像素验证仍是算法证据，真实暗场RAW噪声与变化仍是暗光接收证据；这两者也不能代替正常光照的真实CFA/颜色标定。

试验恢复媒体图、全部格式和控制；完整模式参数已恢复N，WirePlumber恢复，内核taint与五类fault增量0。[恢复记录](pattern-layout-full-finish-validation.json)。完整模式继续保留实验开关，默认关闭。
