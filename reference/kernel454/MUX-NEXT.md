# 454：前摄／第五单色摄像头的共享资源审查

这是对当前源码和 Image363 配置的只读审查，不是已集成驱动。[15份输入指纹](mux-inspection.json)、[源码锚点及边界](mux-validation.json)由 inspect-shared-mux.py 在存储守卫后产生；完整源码副本只留私有 kernel454/shared-mux。未访问手机、占用 SDK、修改共享源码／DT／配置或切换引脚。

本机原厂描述显示 IMX471 与 Shine OV02A1B 共用 MCLK2、GPIO12 reset、GPIO29 路由和 CSI-PHY2；前摄路由为高、单色为低，分别为四条／一条 D-PHY 数据线。二者不能以各自独立 GPIO 消费者直接并列接入。

## 当前代码的具体冲突

IMX471 probe 使用 GPIOD_OUT_HIGH 获取 reset，取得时已改变电平；power_on 先选择 default pinctrl 再开电源／时钟／解除 reset，power_off 则关时钟、置 reset、关电源、选择 sleep pinctrl。当前 DTS 的这些状态还写 GPIO29 和 MCLK 引脚。即使只在 s_stream 周围加锁，另一个 sensor 的 probe、空闲或失败回退仍能改变正在使用的资源。设备核心在 probe 前选择 pinctrl 的情况同样需要消除，不能只改 runtime callback。

Linux 当前已有 mux-gpio 和 mux consumer：mux_state_try_select 使用同一控制器的信号量，冲突返回 -EBUSY，成功后一直独占到 deselect。GPIO29 应只有 mux provider 持有；两 sensor 不能再在 default/sleep pinctrl 或 gpiod 中写它。共享 MCLK 引脚的功能配置也要移出各 sensor 的 sleep 转换，时钟引用仍走 common clock 框架。

reset core 已有 reset-gpios fallback：用完整 fwnode GPIO 参数去重，只创建一个 reset.gpio auxiliary provider；provider 是唯一 gpiod 持有者。不能另造同名 DT compatible 节点冒认这个辅助驱动。可选择标准 shared reset，并严格配对成功 deassert／assert；shared 初次直接 assert 会触发不平衡错误。也可让两个消费者取得 exclusive_released reset，在 route 独占后 acquire，完成断电后 release。两种方式都要求先统一改造前摄，移除直接 GPIO 获取及 pinctrl 电平写入；不能让旧前摄和新 provider 同时争用 GPIO12。provider 首次 probe 会 assert，因此也不能在旧前摄运行时临时创建它。

资源租约必须在任何可能改变路由、reset、MCLK 或供电的操作前取得，维持到断电收尾完成；仅包住 stream-on/off 不足。失败路径应只撤销本次成功取得的引用，并覆盖 probe、runtime resume/suspend 和 remove。mux deselect 即使 idle 切换报错也会解锁，因此不能用“返回错误后仍独占”作为电源故障隔离依据。具体故障保留策略仍须在候选中实现并审查。

## 媒体拓扑与 lane 配置

当前 CAMSS 在 notifier bound 时一次赋值 csiphy->cfg.csi2，complete 为每个外部实体建立 immutable＋enabled 链接。把两个 sensor endpoint 指向 PHY2，会覆盖同一 cfg 指针并产生两个不能正常选择的输入；静态 DTS 增加节点不足以实现切换。

更小的底层方向是保留每个外部 sensor 的 endpoint 配置，把共享 PHY 的输入改为互斥可选媒体链接，在停流状态的 link_setup 按所选 sensor 切换 CSI lane 配置；拒绝活跃时更换输入，停流／失败时恢复对应所有权。当前 libcamera 的图遍历和 configurePath 已会找到路径、关闭可变竞争链接再启用所选路径，可作为接口基础；这仍需实际候选和枚举／开停流验证，不能由源码审查声称兼容。

现有 video-mux 虽可选择输入并传播 Y10 格式，但 Image363 未启用 CONFIG_VIDEO_MUX；它也不提供按前后输入动态改变 CAMSS lane 配置。若采用它仍需改 CAMSS、处理 probe 时的电源租约，且不能让 video-mux 与 sensor 两方重复获取同一 mux 锁。现阶段没有通过增加该节点解决上述问题。

CSIPHY 当前格式表已有 Y10，不能因此认为整个单色链路已通。当前 camss-vfe 模式选择只列四种 Bayer10，RAW 支路又按 SRGGB10P 发现；CSID／VFE、RAW buffer 像素语义和 libcamera 单色配置尚需逐层核对。第五摄像头应保留原厂 BAYER_Y 语义，不能借彩色 Bayer 声明绕过限制或直接套主摄调校。共享资源／RAW 捕获先成立，再接入它自己的 ISP 数据。

下一步实现应限于私有内核候选：标准 mux/reset 消费、共享引脚单一所有者、CAMSS 输入与 lane 选择，连同新 OV02A1B sensor 驱动及单色 RAW 接口。先验证前摄独用及冲突返回，再验证第五探测／原厂表／捕获／停流；当前前摄可用路径必须有原 DT／模块回退。本次没有生成可部署 DT 或完整第五 sensor 模块。
