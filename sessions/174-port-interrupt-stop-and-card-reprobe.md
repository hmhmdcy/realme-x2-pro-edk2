# 174：端口中断停止回归与声卡重探测

2026-10-14。kernel174/logdump174 已部署，boot/DTB172与UCM173保持。声卡手工重绑后，8次录音启停、3次真实暂停恢复、原生四例和普通用户paplay+parecord双向检出左右编码音；WCD underflow/overflow/Port Closed总数0，最终PCM关闭、两功放8/8配平、taint0。

本轮还出现两项未闭环缺陷：在旧172中读取regmap debugfs name触发Oops，受控重启恢复；174首启codec重探测后machine残留jack_component导致声卡注册-EINVAL，手工unbind/bind恢复。当前结果依赖这次声卡恢复，不能记为正常重探测或启动验收。ASoC link exit在component remove之前，card remove在其后，后续jack清理要按此顺序实现。

UCM173默认profile在恢复172后自动加载；端口切换模块被callaudiod主动卸载，属于路由策略所有权，未修改启动配置强制重载。用户暂缺耳机；实物耳机、音质、冷启动/休眠及长期验证仍开放。

完整修改、58项C测试、构建/刷写、失败及来源核验见[174证据](../reference/kernel174/README.md)。此前[173路由及双向](173-ucm-headset-routing-and-desktop-duplex.md)、[172初始化](../reference/kernel172/README.md)、[171人工听音](../reference/kernel171/README.md)保留原测量范围。
