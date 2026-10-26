# 303：硬件AE与联合控制的实机验证

候选复用通用libipa AGC。上一#298启动实际完成联合恒EV480帧、硬件AE隔离／签名线程960帧，17生效revision、34写入和81可辨响应域同帧核对。低照度达到传感器上限，目标亮度收敛未验证；固定WB、其它模式及完整IQ待办。主机DSO／线程合成1440帧另列。

[来源、实机、保留失败和边界](../reference/kernel303/README.md)。305重连后启动ID已变，当前用305新guard；303候选未安装，产品RAW＋CPU ISP。[当前部署](../reference/kernel305/README.md)。
