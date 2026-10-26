# EUD原厂接口与USB预算：离线核对

复用本机已有 `E:/eud-host/quic-eud`，实际HEAD为 `693741a3b0448690402539ed0e6af067510e386f`，origin为Qualcomm的[quic/eud](https://github.com/quic/eud/tree/693741a3b0448690402539ed0e6af067510e386f)，工作区无改动。定向联网只用于确认原厂来源，没有重新克隆、运行EUD工具或操作手机。

[原厂ctl_api.h](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/inc/ctl_api.h)列出VBUS_ATTACH、VBUS_INT、CHGR_EN、CHGR_INT和HOST_EUD_DIS状态位。[ctl_api.cpp](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/ctl_api.cpp)中spoof_attach/detach及enable/disable_charger会写相应控制位并发送中断，等待芯片软件确认；它们不是只读查询，也不是MP2650限流或主机SET_CONFIGURATION许可接口。

对inc/src定向检索未找到hub bmAttributes/MaxPower或self-powered描述符控制实现，也未找到可直接采用的hub bypass事务。仅有HOST_EUD_DIS位名不足以推出本机运行中切换的安全顺序、数据通路恢复或预算效果。已有367退休流程用于进入bootloader，包含解绑console及关闭EUD，不能原样当正常充电的数据口切换。

因此仍保留[主机只读hub证据](USB-HOST-POWER.md)的有限结论：总线供电EUD中间hub是SDP500未获接受的候选因素；缺失败当时的端口状态，尚未证明因果。下一次源预算实验须记录真实NCM父端口与主机ConnectionStatus，并等待合法native回调，不用EUD伪VBUS/充电中断冒充真实供电事件，也不修改Windows预算规则。

该核对没有解决SDP500或USB自动恢复；当前r5仍使用已接受的native100mA。EUD/console准备延迟另见[实际内核审计](../charging-oem-audit-20261023/pm-preparation-gap/README.md)，不能以原厂API名称代替本机驱动调用证据。
