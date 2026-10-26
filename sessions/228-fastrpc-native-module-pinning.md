# 228：FastRPC新启动、保活与五路传感器实测

2026-10-16。受控重启未刷写，boot219镜像/Image183及相机r13/r8保持，启动身份更新到228。实际验证模块保活1→2→1、五类SSC流、活动Wayland用户三类Claim/Release。无WARN/Oops/GPU/DSP/BT重组故障。

外部M=模块产生O/4096，第一观察器失败保留。已真实树内构建并暂存默认2abde，机器代码与已测7ca5一致，仍需下一次启动验taint0。首次UID-only策略拒绝和重启脚本路径错误均保留并按明确状态恢复。[证据](../reference/kernel228/README.md)、[内核完整源与锁](../linux-port/ssc/kernel/README.md)。

用户随后要求利用白天检验前摄颜色，见[229](229-daylight-front-camera-colour.md)；全外设适配目标继续active。
