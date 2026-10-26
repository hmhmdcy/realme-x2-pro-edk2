# 479：mode2 曝光／增益两帧响应的实测依据

[独立报告](HARDWARE.md)与[验收数据](hardware-validation.json)补齐长焦原厂4208×2368 mode2的控制响应：九次曝光／模拟增益升降，首变化及首个三帧平台均为写入SOF＋2。九步都满足306既有SNR与响应幅度条件，无缺SOF、pending、失败或跨下一SOF写入。

依据为真实控制写入和同SOF的上游线性BHIST；没有使用始终为startup 500／64的曝光／增益metadata。当前468私有原厂mode2 profile已有exposure_delay=2、gain_delay=2，数值与本次记录精度内的响应一致，因此不改原厂profile或控制算法。本测量关闭AE／DelayedControls，不代替自动控制开启后的整链验证。

476原事务的`passed=false`保持：其工具错误要求零IPE，而461对processed输出默认启用单遍IPE。本轮240次IPE均成功，动态tone参数为空、PD10关闭；BHIST在IPE排队前已解析保存，能独立分析上述响应，但不能称为无IPE隔离测量。原因与最初离线快审更正见[478](../kernel478/ipe-r1-correction.md)。未为修改报告重新采集。

正式sensor、434模块、440 r32／r27及服务已恢复，外部R8健康检查通过，fault0／taint0；全部实际样本和源码片段仅在私有输出目录。没有额外饱和事实，均值不能排除局部剪切；逐像素／寄存器锁存、其它控制范围、光学LSC、AWB／AF、录像与多摄仍按各自范围验证。

原件位于`E:/edk2-samurai-out/kernel476/runtime-collected-r1`，29文件归档SHA256 `00f825783bb16d090161e51c402414d06a82383e7d7ccba863e2eb9b5ad13389`；[inspect-control.py](inspect-control.py)只读取缓存，复算真实响应并保留原始失败。
