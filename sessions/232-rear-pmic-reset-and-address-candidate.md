# 232：后摄 PM8008 复位/地址依赖候选

后摄P/Q独占复位、同地址初始化顺序、supplier解绑竞态及P失败清理已实现。两个匹配ABI的树内模块、97例实际函数故障测试、三个有效负对照、两份精确设备树及仅改变内嵌DTB的启动镜像已完成。

实机仍使用boot230和原有Q，taint/fault0。没有安装、刷写或重启。未知VIN未猜测，实验P仅探测身份并跳过全部MFD children，后摄未出图。下一步受控暂存/切换后验收，完整目标仍active。

[代码、构建和实机收据](../reference/kernel232/README.md)、[实验契约](../reference/kernel232/RESET-CONTRACT.md)。
